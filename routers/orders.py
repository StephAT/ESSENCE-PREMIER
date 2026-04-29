import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database.supabase_client import get_supabase_admin
from models.schemas import (
    CheckoutRequest, Order, OrderListItem, OrderItem, MessageResponse, DeliveryOption
)
from dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/orders", tags=["Orders"])

VAT_RATE = 0.15

DELIVERY_FEES = {
    DeliveryOption.standard: 0.0,    # Free
    DeliveryOption.express: 50.0,    # GHS equivalent
    DeliveryOption.same_day: 120.0,
}


def _generate_reference() -> str:
    """Generate a human-readable order reference: EP-XXXX-XXXX"""
    uid = uuid.uuid4().hex[:8].upper()
    return f"EP-{uid[:4]}-{uid[4:]}"


@router.post("", response_model=Order, status_code=201)
async def place_order(payload: CheckoutRequest, auth: dict = Depends(get_current_user)):
    """
    Convert the user's cart into a confirmed order.
    Steps:
      1. Fetch cart items
      2. Verify stock for each item
      3. Decrement stock
      4. Create order + order_items rows
      5. Clear cart
    """
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # 1. Fetch cart
    cart_resp = (
        admin.table("cart_items")
        .select("*, products(id, sku, name, price, unit, image_url, stock)")
        .eq("user_id", user_id)
        .execute()
    )

    if not cart_resp.data:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    # 2. Verify stock
    for row in cart_resp.data:
        p = row.get("products", {})
        if row["quantity"] > p.get("stock", 0):
            raise HTTPException(
                status_code=400,
                detail=f"'{p['name']}' only has {p['stock']} units in stock."
            )

    # 3. Calculate totals
    order_items_data = []
    subtotal = 0.0

    for row in cart_resp.data:
        p = row.get("products", {})
        qty = row["quantity"]
        unit_price = p.get("price", 0)
        item_subtotal = round(unit_price * qty, 2)
        subtotal += item_subtotal
        order_items_data.append({
            "product_id": p["id"],
            "sku": p.get("sku", ""),
            "name": p.get("name", ""),
            "quantity": qty,
            "unit_price": unit_price,
            "subtotal": item_subtotal,
            "image_url": p.get("image_url"),
        })

    subtotal = round(subtotal, 2)
    vat_amount = round(subtotal * VAT_RATE, 2)
    delivery_fee = DELIVERY_FEES.get(payload.delivery_option, 0.0)
    total = round(subtotal + vat_amount + delivery_fee, 2)

    # 4. Create order
    reference = _generate_reference()
    order_row = {
        "user_id": user_id,
        "reference": reference,
        "status": "pending",
        "subtotal": subtotal,
        "vat_amount": vat_amount,
        "delivery_fee": delivery_fee,
        "total": total,
        "delivery_option": payload.delivery_option.value,
        "payment_method": payload.payment_method.value,
        "delivery_address": payload.delivery_address.model_dump(),
        "notes": payload.notes,
    }

    try:
        order_resp = admin.table("orders").insert(order_row).execute()
        order_id = order_resp.data[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

    # 5. Insert order items
    for item in order_items_data:
        item["order_id"] = order_id

    try:
        admin.table("order_items").insert(order_items_data).execute()
    except Exception as e:
        admin.table("orders").delete().eq("id", order_id).execute()
        raise HTTPException(status_code=500, detail="Failed to save order items.")

    # 6. Decrement stock
    for row in cart_resp.data:
        p = row.get("products", {})
        new_stock = p.get("stock", 0) - row["quantity"]
        admin.table("products").update({"stock": max(new_stock, 0)}).eq("id", p["id"]).execute()

    # 7. Clear cart
    admin.table("cart_items").delete().eq("user_id", user_id).execute()

    # 8. Return full order
    return Order(
        id=order_id,
        reference=reference,
        status="pending",
        items=[OrderItem(**i) for i in order_items_data],
        subtotal=subtotal,
        vat_amount=vat_amount,
        delivery_fee=delivery_fee,
        total=total,
        delivery_option=payload.delivery_option.value,
        payment_method=payload.payment_method.value,
        delivery_address=payload.delivery_address.model_dump(),
        notes=payload.notes,
        created_at=order_resp.data[0]["created_at"],
    )


@router.get("", response_model=List[OrderListItem])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    auth: dict = Depends(get_current_user),
):
    """List all orders for the current user, most recent first."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    offset = (page - 1) * page_size

    try:
        resp = (
            admin.table("orders")
            .select("id, reference, status, total, created_at, order_items(id)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

    results = []
    for o in resp.data:
        results.append(OrderListItem(
            id=o["id"],
            reference=o["reference"],
            status=o["status"],
            item_count=len(o.get("order_items", [])),
            total=o["total"],
            created_at=o["created_at"],
        ))

    return results


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str, auth: dict = Depends(get_current_user)):
    """Get full details of a specific order."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("orders")
            .select("*, order_items(*)")
            .eq("id", order_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Order not found.")

    o = resp.data
    return Order(
        id=o["id"],
        reference=o["reference"],
        status=o["status"],
        items=[OrderItem(**i) for i in o.get("order_items", [])],
        subtotal=o["subtotal"],
        vat_amount=o["vat_amount"],
        delivery_fee=o["delivery_fee"],
        total=o["total"],
        delivery_option=o["delivery_option"],
        payment_method=o["payment_method"],
        delivery_address=o["delivery_address"],
        notes=o.get("notes"),
        created_at=o["created_at"],
        updated_at=o.get("updated_at"),
    )


@router.patch("/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(order_id: str, auth: dict = Depends(get_current_user)):
    """Cancel a pending or confirmed order."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("orders")
            .select("id, status")
            .eq("id", order_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Order not found.")

    o = resp.data
    if o["status"] not in ("pending", "confirmed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status '{o['status']}'."
        )

    admin.table("orders").update({"status": "cancelled"}).eq("id", order_id).execute()

    return MessageResponse(message=f"Order cancelled successfully.")
