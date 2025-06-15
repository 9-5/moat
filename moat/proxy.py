import aiohttp
from fastapi import Request, Response as FastAPIResponse
from starlette.responses import StreamingResponse
from urllib.parse import urljoin, urlparse
from typing import Optional, AsyncGenerator
import asyncio

from .service_registry import registry as global_registry
from .config import get_settings

# Headers to remove from client request before sending to backend.
HOP_BY_HOP_HEADERS_AND_HOST = [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'host'
]

# Headers to remove from backend response before sending to client.
# aiohttp handles decompression by default, so Content-Encoding from backend is typically removed.
RESPONSE_HOP_BY_HOP_HEADERS = [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'content-encoding',
    'content-length'
]


async def _stream_aiohttp_response_content(
    backend_response: aiohttp.ClientResponse,
    request_url_for_log: str
) -> AsyncGenerator[bytes, None]:
    print(f"DEBUG AIOHTTP Streamer: Starting to stream content from: {backend_response.url} for original request: {request_url_for_log}")
    chunk_count = 0
    total_bytes_yielded = 0
    try:
        async for chunk in backend_response.content.iter_any(): # iter_any() reads available data
            chunk_count += 1
            chunk_len = len(chunk)
            total_bytes_yielded += chunk_len
            yield chunk

        if chunk_count == 0 and backend_response.headers.get('Content-Length', '0') != '0' and backend_response.status not in [204, 304]:
            print(f"WARNING AIOHTTP Streamer: No chunks yielded for {backend_response.url} but content was expected "
                  f"(status: {backend_response.status}, content-length: {backend_response.headers.get('Content-Length')}).")
        else:
            print(f"DEBUG AIOHTTP Streamer: Finished iter_any loop, yielded {chunk_count} chunks, total {total_bytes_yielded} bytes for {backend_response.url}")

    except aiohttp.ClientError as e:
        print(f"ERROR in AIOHTTP Streamer (ClientError from {backend_response.url}): {type(e).__name__} - {e!r}")
        # Let StreamingResponse handle the broken stream from the client's perspective.
    except Exception as e:
        print(f"ERROR in AIOHTTP Streamer (Other error from {backend_response.url}): {type(e).__name__} - {e!r}")
    finally:
        print(f"DEBUG AIOHTTP Streamer: finally block. Releasing backend_http_response for: {backend_response.url}")
        # For aiohttp, response.release() is important to free up the connection from the pool.
        backend_response.release()


async def reverse_proxy(request: Request):
    raw_host_header = request.headers.get("host")
    if not raw_host_header:
        print(f"--- Proxy Attempt --- [Error: No Host Header for {request.url}]")
        return FastAPIResponse("Host header missing", status_code=400)

    lookup_hostname = raw_host_header.split(":")[0]
    print(f"--- Proxy Attempt --- [Client Host: '{raw_host_header}', Lookup Host: '{lookup_hostname}', Path: '{request.url.path}']")

    target_base_url_str = await global_registry.get_target_url(lookup_hostname)
    if not target_base_url_str:
        print(f"Proxy Error: No target for '{lookup_hostname}'. Registry: {await global_registry.get_all_services()}")
        return FastAPIResponse(f"Service not found for hostname: {lookup_hostname}", status_code=404)
    print(f"Proxy Info: Found target '{target_base_url_str}' for '{lookup_hostname}'")

    backend_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS_AND_HOST
    }

    backend_request_path = request.url.path
    if request.url.query:
        backend_request_path += f"?{request.url.query}"
    base_for_join = target_base_url_str.rstrip('/') + '/'
    path_for_join = backend_request_path.lstrip('/')
    full_target_url_for_request = urljoin(base_for_join, path_for_join)

    print(f"DEBUG Proxy: Constructed full_target_url_for_request: '{full_target_url_for_request}'")
    try:
        parsed_target_url = urlparse(full_target_url_for_request)
        target_actual_hostname = parsed_target_url.hostname
        if not target_actual_hostname:
            raise ValueError(f"Could not extract hostname from parsed URL object: {parsed_target_url}")
        backend_headers["Host"] = target_actual_hostname
    except Exception as e:
        print(f"Proxy Error: Could not parse target hostname from '{full_target_url_for_request}': {e!r}")
        return FastAPIResponse("Invalid backend target URL configuration.", status_code=502)

    client_host_ip = request.client.host if request.client else "unknown"
    backend_headers["X-Forwarded-For"] = request.headers.get("x-forwarded-for", client_host_ip)
    x_forwarded_proto_header = request.headers.get("x-forwarded-proto")
    effective_scheme = x_forwarded_proto_header if x_forwarded_proto_header else request.url.scheme
    backend_headers["X-Forwarded-Proto"] = effective_scheme
    backend_headers["X-Forwarded-Host"] = request.headers.get("x-forwarded-host", raw_host_header)
    x_fwd_host_val_for_port = backend_headers["X-Forwarded-Host"]
    if ':' in x_fwd_host_val_for_port:
        original_port_str = x_fwd_host_val_for_port.split(':')[-1]
    else:
        original_port_str = str(request.url.port or (80 if effective_scheme == 'http' else 443))
    backend_headers["X-Forwarded-Port"] = request.headers.get("x-forwarded-port", original_port_str)
    backend_headers["X-Real-IP"] = request.headers.get("x-real-ip", client_host_ip)

    print(f"Proxying with AIOHTTP: {request.method} '{raw_host_header}{backend_request_path}' -> '{full_target_url_for_request}' "
          f"(Outgoing Backend Headers will include Host: '{backend_headers['Host']}')")

    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10, sock_read=60)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            request_body_bytes = await request.body()
            data_to_send = request_body_bytes if request_body_bytes and request.method not in ["GET", "HEAD", "DELETE"] else None

            print(f"DEBUG AIOHTTP Proxy: Sending request to backend: {request.method} {full_target_url_for_request}")
            # The response from session.request() is a context manager itself
            async with session.request(
                request.method,
                full_target_url_for_request,
                headers=backend_headers,
                data=data_to_send,
                allow_redirects=False
            ) as backend_aiohttp_response: # backend_aiohttp_response will be released on exiting this block

                print(f"DEBUG AIOHTTP Proxy: Received headers from backend {backend_aiohttp_response.url}: {backend_aiohttp_response.status}, Headers: {dict(backend_aiohttp_response.headers)}")

                # Convert CIMultiDictProxy to regular dict for consistent header processing
                response_headers_from_backend = dict(backend_aiohttp_response.headers)
                client_response_headers = {
                    k: v for k, v in response_headers_from_backend.items() if k.lower() not in RESPONSE_HOP_BY_HOP_HEADERS
                }

                if backend_aiohttp_response.status == 204: # No content
                    print(f"DEBUG AIOHTTP Proxy: Backend responded with 204 No Content for {backend_aiohttp_response.url}.")
                    # No body to stream, aiohttp response context manager will handle release.
                    return FastAPIResponse(status_code=204, headers=client_response_headers)

                content_length_str = response_headers_from_backend.get('Content-Length')
                connection_header_from_backend = response_headers_from_backend.get('Connection', '').lower()
                small_response_threshold = 1 * 1024 # 1KB

                should_read_fully = False
                if connection_header_from_backend == 'close':
                    print(f"DEBUG AIOHTTP Proxy: Backend sent 'Connection: close'. Will attempt to read response fully.")
                    should_read_fully = True
                elif content_length_str and content_length_str.isdigit():
                    content_length = int(content_length_str)
                    if 0 < content_length < small_response_threshold: # Only consider non-empty small responses
                        print(f"DEBUG AIOHTTP Proxy: Small response (Content-Length: {content_length} < {small_response_threshold}). Will attempt to read fully.")
                        should_read_fully = True
                
                if should_read_fully:
                    print(f"DEBUG AIOHTTP Proxy: Reading response fully for {backend_aiohttp_response.url}.")
                    try:
                        full_body = await backend_aiohttp_response.read() # Reads entire body
                        # .read() consumes the content and the response is typically released by aiohttp
                        print(f"DEBUG AIOHTTP Proxy: Read full body of size {len(full_body)}.")
                        return FastAPIResponse(
                            content=full_body,
                            status_code=backend_aiohttp_response.status,
                            headers=client_response_headers, # These now exclude original C-L and C-E
                            media_type=response_headers_from_backend.get("Content-Type")
                        )
                    except aiohttp.ClientError as read_err_during_full_read: # Catch aiohttp client errors
                        print(f"ERROR AIOHTTP Proxy: ClientError during full read from {backend_aiohttp_response.url} (Status: {backend_aiohttp_response.status}): {read_err_during_full_read!r}")
                        # If reading fully fails (e.g. connection drops mid-read),
                        # we cannot fall back to streaming if 'Connection: close' was the reason.
                        # Re-raise to be caught by the outer specific aiohttp error handlers.
                        raise
                
                # If not read_fully, then stream:
                print(f"DEBUG AIOHTTP Proxy: Using streaming for response from {backend_aiohttp_response.url}")
                # Pass the response object to the generator. The generator will call .release()
                return StreamingResponse(
                    _stream_aiohttp_response_content(backend_aiohttp_response, str(request.url)),
                    status_code=backend_aiohttp_response.status,
                    headers=client_response_headers,
                    media_type=response_headers_from_backend.get("Content-Type")
                )

        # Exception handling for aiohttp client errors
        except aiohttp.ClientConnectorError as e:
            print(f"Proxy Error (AIOHTTP ClientConnectorError) to '{full_target_url_for_request}': {e!r}")
            return FastAPIResponse(f"Upstream service connection error for {lookup_hostname}", status_code=503) # Service Unavailable
        except aiohttp.ClientResponseError as e: # Should ideally not be hit if status is passed through
            print(f"Proxy Error (AIOHTTP ClientResponseError) from '{full_target_url_for_request}': Status {e.status}, Message: {e.message!r}, Headers: {e.headers}")
            return FastAPIResponse(f"Upstream service responded with error {e.status} for {lookup_hostname}", status_code=e.status if e.status >= 400 else 502)
        except asyncio.TimeoutError as e: # Can be raised by aiohttp ClientTimeout (covers ServerTimeoutError as well)
            print(f"Proxy Error (AIOHTTP TimeoutError) for '{full_target_url_for_request}': {e!r}")
            return FastAPIResponse(f"Upstream service timeout for {lookup_hostname}", status_code=504) # Gateway Timeout
        except aiohttp.ClientError as e: # More generic aiohttp client error
            print(f"Proxy Error (AIOHTTP ClientError) for '{full_target_url_for_request}': {type(e).__name__} - {e!r}")
            status_code_to_return = 502 # Default Bad Gateway for client errors
            # ServerTimeoutError is a subclass of ClientOSError, which is a ClientError
            if isinstance(e, (aiohttp.ServerTimeoutError, asyncio.TimeoutError)): # Redundant check, but safe
                status_code_to_return = 504
            elif isinstance(e, (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError)):
                 print(f"Proxy Error: Server disconnected or connection error for {full_target_url_for_request}")
                 # Keep 502 for these, or consider 503 if it implies temporary unavailability
            return FastAPIResponse(f"AIOHTTP client error communication with {lookup_hostname}", status_code=status_code_to_return)
        except Exception as e:
            print(f"Proxy Error (Unexpected) while proxying with AIOHTTP to '{full_target_url_for_request}': {type(e).__name__} - {e!r}")
            return FastAPIResponse(f"General proxy error for {lookup_hostname}: {type(e).__name__}", status_code=500)
        # `session` (aiohttp.ClientSession) is closed by its `async with`.
        # `backend_aiohttp_response` is closed by its `async with` or by the streamer's `release()`
        # or by `backend_aiohttp_response.read()` in the "read_fully" case.
