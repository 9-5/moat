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
    'content-encoding', # Important: aiohttp auto-decompresses. If backend sends this, browsers may incorrectly handle it.
]

async def stream_response(backend_aiohttp_response: aiohttp.ClientResponse) -> AsyncGenerator[bytes, None]:
    """
    Streams data from the backend response to the client.