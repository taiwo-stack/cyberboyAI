import asyncio
from tools.trusted_domains import trusted_domain_manager

async def add_domains():
    await trusted_domain_manager.add("kaggle.com", "Kaggle")
    await trusted_domain_manager.add("huggingface.co", "HuggingFace")
    print("Added domains to whitelist.")

if __name__ == "__main__":
    asyncio.run(add_domains())
