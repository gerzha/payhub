from fastapi import FastAPI

from src.api.v1 import orders, webhooks


def create_app() -> FastAPI:
    app = FastAPI(title="payhub")

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "pong"}

    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")

    return app


app = create_app()
