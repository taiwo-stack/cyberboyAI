import asyncio
from agents.brand_agent import BrandAgent

async def test():
    b = BrandAgent()
    res = await b.check('http://dhl-customs-fee.com/pay?id=123')
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
