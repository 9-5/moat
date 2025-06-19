import aiohttp
import asyncio # Added asyncio for TimeoutError specifically
from fastapi import Request, Response as FastAPIResponse
from starlette.responses import StreamingResponse
from urllib.parse import urljoin, urlparse
from typing import AsyncGenerator

from .service_registry import registry as global_registry
from .config import get_settings

# Headers to remove from client request before sending to backend.
HOP_BY_HOP_HEADERS_AND_HOST = [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'host' # Host header is reconstructed based on the target_url
]

# Headers to remove from backend response before sending to client.
RESPONSE_HOP_BY_HOP_HEADERS = [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'content-encoding', 
    'content-length'    
]


async def _stream_aiohttp_response_content( # This generator might not be used if we fully read below
    backend_response: aiohttp.ClientResponse,
    request_url_for_log: str 
) -> AsyncGenerator[bytes, None]:
    # print(f"DEBUG AIOHTTP Streamer: Starting to stream content from: {backend_response.url} for original request: {request_url_for_log}")
    try:
        async for chunk in backend_response.content.iter_any():
            if chunk: 
                yield chunk
        # print(f"DEBUG AIOHTTP Streamer: Finished iter_any loop for {backend_response.url}")
    except aiohttp.ClientError as e:
        print(f"ERROR in AIOHTTP Streamer (ClientError from {backend_response.url}): {type(e).__name__} - {e!r}")
        raise 
    except Exception as e:
        print(f"ERROR in AIOHTTP Streamer (Other error from {backend_response.url}): {type(e).__name__} - {e!r}")
        raise
    finally:
        # print(f"DEBUG AIOHTTP Streamer: finally block. Releasing backend_response for: {backend_response.url}")
        if not backend_response.closed:
            backend_response.release()


async def reverse_proxy(request: Request):
    raw_host_header = request.headers.get("host")
    if not raw_host_header:
        return FastAPIResponse("Host header missing", status_code=400)

    lookup_hostname = raw_host_header.split(":")[0]

    target_base_url_str = await global_registry.get_target_url(lookup_hostname)
    if not target_base_url_str:
        print(f"Proxy Error: No target for '{lookup_hostname}'. Registry: {await global_registry.get_all_services()}")
        return FastAPIResponse(f"Service not found for hostname: {lookup_hostname}", status_code=404)

    backend_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS_AND_HOST
    }

    backend_request_path = request.url.path
    if request.url.query:
        backend_request_path += f"?{request.url.query}"
    
    base_for_join = target_base_url_str if target_base_url_str.endswith('/') else target_base_url_str + '/'
    path_for_join = backend_request_path.lstrip('/')
    full_target_url_for_request = urljoin(base_for_join, path_for_join)

    try:
        parsed_target_url = urlparse(full_target_url_for_request)
        target_actual_hostname_for_header = parsed_target_url.hostname
        if parsed_target_url.port and \
           not (parsed_target_url.scheme == 'http' and parsed_target_url.port == 80) and \
           not (parsed_target_url.scheme == 'https' and parsed_target_url.port == 443):
            target_actual_hostname_for_header += f":{parsed_target_url.port}"
        
        if not target_actual_hostname_for_header:
            raise ValueError(f"Could not extract hostname from parsed URL object: {parsed_target_url}")
        backend_headers["Host"] = target_actual_hostname_for_header
    except Exception as e:
        print(f"Proxy Error: Could not parse target hostname from '{full_target_url_for_request}': {e!r}")
        return FastAPIResponse("Invalid backend target URL configuration.", status_code=502)

    client_host_ip = request.client.host if request.client else "unknown"
    backend_headers["X-Forwarded-For"] = request.headers.get("x-forwarded-for", client_host_ip)
    x_forwarded_proto_header = request.headers.get("x-forwarded-proto")
    effective_scheme = x_forwarded_proto_header if x_forwarded_proto_header else request.url.scheme
    backend_headers["X-Forwarded-Proto"] = effective_scheme
    backend_headers["X-Forwarded-Host"] = request.headers.get("x-forwarded-host", raw_host_header)
    x_fwd_host_val = backend_headers["X-Forwarded-Host"]
    if ':' in x_fwd_host_val:
        original_port_str = x_fwd_host_val.split(':')[-1]
    else:
        original_port_str = str(request.url.port or (80 if effective_scheme == 'http' else 443))
    backend_headers["X-Forwarded-Port"] = request.headers.get("x-forwarded-port", original_port_str)
    backend_headers["X-Real-IP"] = request.headers.get("x-real-ip", client_host_ip)

    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10, sock_read=300)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            request_body_bytes = await request.body()
            data_to_send = request_body_bytes if request.method not in ["GET", "HEAD", "DELETE", "OPTIONS"] else None

            # print(f"DEBUG AIOHTTP Proxy: Sending request to backend: {request.method} {full_target_url_for_request}")
            async with session.request(
                request.method,
                full_target_url_for_request,
                headers=backend_headers,
                data=data_to_send,
                allow_redirects=False 
            ) as backend_aiohttp_response:

                # print(f"DEBUG AIOHTTP Proxy: Received headers from backend {backend_aiohttp_response.url}: {backend_aiohttp_response.status}, Headers: {dict(backend_aiohttp_response.headers)}")

                response_headers_from_backend = dict(backend_aiohttp_response.headers)
                client_response_headers = {
                    k: v for k, v in response_headers_from_backend.items() if k.lower() not in RESPONSE_HOP_BY_HOP_HEADERS
                }
                
                if backend_aiohttp_response.status in [204, 304]:
                    # print(f"DEBUG AIOHTTP Proxy: Backend responded with {backend_aiohttp_response.status}. No body to stream.")
                    return FastAPIResponse(status_code=backend_aiohttp_response.status, headers=client_response_headers)

                # --- MODIFICATION: Attempt to read full body before streaming to client ---
                try:
                    # print(f"DEBUG AIOHTTP Proxy: Attempting to read full body for {backend_aiohttp_response.url}. Status: {backend_aiohttp_response.status}, Content-Length: {response_headers_from_backend.get('Content-Length')}")
                    full_body = await backend_aiohttp_response.read() # Read the entire body
                    # print(f"DEBUG AIOHTTP Proxy: Successfully read full body of size {len(full_body)} bytes.")
                    
                    # After successful read, the backend_aiohttp_response's content is consumed.
                    # The connection might be released or closed by aiohttp after .read().
                    # FastAPIResponse will set its own Content-Length based on full_body.
                    return FastAPIResponse(
                        content=full_body,
                        status_code=backend_aiohttp_response.status,
                        headers=client_response_headers, 
                        media_type=response_headers_from_backend.get("Content-Type")
                    )
                except aiohttp.ClientError as e_read: 
                    print(f"ERROR AIOHTTP Proxy: ClientError during backend_aiohttp_response.read() for {backend_aiohttp_response.url}: {e_read!r}")
                    # Ensure the response object is released if an error occurs during read
                    if not backend_aiohttp_response.closed:
                        backend_aiohttp_response.release()
                    return FastAPIResponse("Error reading from upstream service.", status_code=502)
                # --- END MODIFICATION ---

        except aiohttp.ClientConnectorError as e:
            print(f"Proxy Error (AIOHTTP ClientConnectorError) to '{full_target_url_for_request}': {e!r}")
            return FastAPIResponse(f"Upstream service connection error for {lookup_hostname}", status_code=503)
        except aiohttp.ClientResponseError as e: 
            print(f"Proxy Error (AIOHTTP ClientResponseError) from '{full_target_url_for_request}': Status {e.status}, Message: {e.message!r}, Headers: {e.headers}")
            return FastAPIResponse(f"Upstream service response error for {lookup_hostname}", status_code=e.status if e.status >= 400 else 502)
        except asyncio.TimeoutError as e: # Covers aiohttp's various timeout errors
            print(f"Proxy Error (AIOHTTP TimeoutError) for '{full_target_url_for_request}': {e!r}")
            return FastAPIResponse(f"Upstream service timeout for {lookup_hostname}", status_code=504)
        except aiohttp.ClientError as e: 
            print(f"Proxy Error (AIOHTTP ClientError) for '{full_target_url_for_request}': {type(e).__name__} - {e!r}")
            status_code_to_return = 502 
            if isinstance(e, (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError)):
                 print(f"Proxy Info: Connection issue with backend {full_target_url_for_request}. Error: {e!r}")
            return FastAPIResponse(f"AIOHTTP client error communicating with {lookup_hostname}", status_code=status_code_to_return)
        except Exception as e:
            print(f"Proxy Error (Unexpected) while proxying with AIOHTTP to '{full_target_url_for_request}': {type(e).__name__} - {e!r}")
            return FastAPIResponse(f"General proxy error for {lookup_hostname}", status_code=500)
