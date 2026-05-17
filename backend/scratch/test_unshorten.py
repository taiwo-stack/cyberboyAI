import asyncio
from tools.url_unshortener import unshorten

async def test():
    url = "https://bit.ly/3U1jA6z"
    final_url, chain = await unshorten(url)
    print(f"Final URL: {final_url}")
    print(f"Chain: {chain}")

if __name__ == "__main__":
    asyncio.run(test())
