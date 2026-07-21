import base64

from fastapi import APIRouter, HTTPException, Request

from src.providers.registry import PROVIDERS
from src.queue.sqs import SQSQueue
from src.settings import settings

router = APIRouter(tags=["webhooks"])

inbound_queue = SQSQueue(settings.inbound_queue_name)


@router.post("/webhooks/{provider}", status_code=202)
async def receive_webhook(provider: str, request: Request) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="unknown provider")

    raw_body = await request.body()
    await inbound_queue.send(
        {
            "provider": provider,
            "raw_body": base64.b64encode(raw_body).decode(),
            "headers": dict(request.headers),
        }
    )
    return {"status": "accepted"}
