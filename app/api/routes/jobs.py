import asyncio
import logging
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from arq import ArqRedis
from app.api.deps.arq import get_arq_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/{job_id}/stream")
async def stream_job_events(job_id: str, request: Request, arq_redis: ArqRedis = Depends(get_arq_redis)):
    """
    Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job.
    """
    channel_name = f"research:{job_id}"
    
    async def event_generator():
        pubsub = arq_redis.pubsub()
        await pubsub.subscribe(channel_name)
        try:
            logger.info(f"Client connected to SSE stream for job: {job_id}")
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream for job: {job_id}")
                    break
                    
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    data = message['data'].decode('utf-8')
                    yield f"data: {data}\n\n"
                    
                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in ("completed", "failed"):
                            logger.info(f"Job {job_id} {parsed.get('status')}. Closing stream.")
                            break
                    except json.JSONDecodeError:
                        pass
                
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
