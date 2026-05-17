import time
from typing import Any, Dict, Optional

# In-memory storage: {key: {"value": any, "expiry": timestamp}}
_cache: Dict[str, Dict[str, Any]] = {}

async def get(key: str) -> Optional[Any]:
    """Retrieves an item from cache if it exists and hasn't expired."""
    item = _cache.get(key)
    if not item:
        return None
    
    if time.time() > item["expiry"]:
        del _cache[key]
        return None
        
    return item["value"]

async def set(key: str, value: Any, ttl_seconds: int = 3600):
    """Sets an item in cache with a specific TTL."""
    _cache[key] = {
        "value": value,
        "expiry": time.time() + ttl_seconds
    }

async def delete(key: str):
    """Deletes an item from cache."""
    if key in _cache:
        del _cache[key]
