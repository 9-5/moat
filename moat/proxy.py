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
RESPONSE_HOP_BY_HOP_HE
... (FILE CONTENT TRUNCATED) ...
   # Keep 502 for these, or consider 503 if it implies temporary unavailability
            return FastAPIResponse(f"AIOHTTP client error communication with {lookup_hostname}", status_code=status_code_to_return)
        except Exception as e:
            print(f"Proxy Error (Unexpected) while proxying with AIOHTTP to '{full_target_url_for_request}': {type(e).__name__} - {e!r}")
            return FastAPIResponse(f"General proxy error for {lookup_hostname}: {type(e).__name__}", status_code=500)
        # `session` (aiohttp.ClientSession) is closed by its `async with`.
        # `backend_aiohttp_response` is closed by its `async with` or by the streamer's `release()`
        # or by `backend_aiohttp_response.read()` in the "read_fully" case.