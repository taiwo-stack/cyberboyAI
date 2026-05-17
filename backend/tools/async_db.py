"""
async_db.py — Non-blocking Supabase helper

The supabase-py client is synchronous. Calling it directly from async FastAPI
handlers blocks the entire event loop, stalling all other requests.

This module exposes `db()` — a single async function that runs any supabase
query in a thread executor, keeping the event loop free.

Usage:
    from tools.async_db import db
    result = await db(lambda: supabase.table("foo").select("*").execute())
"""

import asyncio
from functools import partial
from tools.supabase_client import supabase

# Shared executor — bounded so DB queries don't spawn unlimited threads
from concurrent.futures import ThreadPoolExecutor
_db_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="supabase")


async def db(query_fn):
    """
    Run a synchronous supabase query without blocking the event loop.

    Args:
        query_fn: A zero-argument callable that returns a supabase response.
                  Use a lambda or functools.partial to capture arguments.

    Returns:
        The supabase response object.

    Example:
        result = await db(lambda: supabase.table("nigerian_brands").select("*").execute())
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_db_executor, query_fn)
