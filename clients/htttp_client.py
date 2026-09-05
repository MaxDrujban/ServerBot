import httpx


async def get_client():
    async with httpx.AsyncClient(timeout=10) as client:
        yield client
