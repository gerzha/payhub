from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Order
from src.db.session import get_session
from src.schemas.order import OrderCreateRequest, OrderResponse

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    request: OrderCreateRequest, session: AsyncSession = Depends(get_session)
) -> Order:
    order = Order(
        product_id=request.product_id,
        provider=request.provider,
        status="PENDING",
        amount=request.amount,
        currency=request.currency,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int, session: AsyncSession = Depends(get_session)
) -> Order:
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order
