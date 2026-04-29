from fastapi import APIRouter, HTTPException, Depends, status
from database.supabase_client import get_supabase_admin
from models.schemas import (
    CartItemAdd, CartItemUpdate, CartResponse, CartItem, MessageResponse
)
from dependencies import get_current_user

router = APIRouter(prefix="/cart", tags=["Cart"])

VAT_RATE = 0.15  # 15% VAT (Ghana standard rate)


def _build_cart_response(items_data: list) -> CartResponse:
    """Convert raw DB cart rows into a CartResponse."""
    items = []
    for row in items_data:
        p = row.get("products", {})
        qty = row["quantity"]
        price = p.get("price", 0)
        items.append(CartItem(
            id=row["id"],
            product_id=row["product_id"],
            sku=p.get("sku", ""),
            name=p.get("name", ""),
            price=price,
            unit=p.get("unit", "unit"),
            quantity=qty,
            subtotal=round(price * qty, 2),
            image_url=p.get("image_url"),
        ))

    subtotal = round(sum(i.subtotal for i in items), 2)
    vat_amount = round(subtotal * VAT_RATE, 2)
    total = round(subtotal + vat_amount, 2)

    return CartResponse(
        items=items,
        item_count=sum(i.quantity for i in items),
        subtotal=subtotal,
        vat_rate=VAT_RATE,
        vat_amount=vat_amount,
        total=total,
    )


@router.get("", response_model=CartResponse)
async def get_cart(auth: dict = Depends(get_current_user)):
    """Return the current user's cart with product details."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("cart_items")
            .select("*, products(id, sku, name, price, unit, image_url, stock)")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch cart: {str(e)}")

    return _build_cart_response(resp.data)


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(payload: CartItemAdd, auth: dict = Depends(get_current_user)):
    """
    Add a product to the cart.
    If it already exists, the quantity is incremented.
    """
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # Verify product exists and has stock
    try:
        prod_resp = admin.table("products").select("id, stock, is_active").eq("id", payload.product_id).single().execute()
        product = prod_resp.data
    except Exception:
        raise HTTPException(status_code=404, detail="Product not found.")

    if not product.get("is_active"):
        raise HTTPException(status_code=400, detail="This product is no longer available.")

    if product.get("stock", 0) < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product['stock']} units available in stock."
        )

    # Check if already in cart
    try:
        existing = (
            admin.table("cart_items")
            .select("id, quantity")
            .eq("user_id", user_id)
            .eq("product_id", payload.product_id)
            .single()
            .execute()
        )
        existing_item = existing.data
    except Exception:
        existing_item = None

    if existing_item:
        new_qty = existing_item["quantity"] + payload.quantity
        if new_qty > product.get("stock", 0):
            raise HTTPException(status_code=400, detail="Not enough stock for requested quantity.")
        admin.table("cart_items").update({"quantity": new_qty}).eq("id", existing_item["id"]).execute()
    else:
        admin.table("cart_items").insert({
            "user_id": user_id,
            "product_id": payload.product_id,
            "quantity": payload.quantity,
        }).execute()

    # Return updated cart
    return await get_cart(auth)


@router.patch("/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: str,
    payload: CartItemUpdate,
    auth: dict = Depends(get_current_user),
):
    """
    Update the quantity of a cart item.
    Setting quantity to 0 removes the item.
    """
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # Verify ownership
    try:
        item_resp = admin.table("cart_items").select("id, product_id").eq("id", item_id).eq("user_id", user_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Cart item not found.")

    if payload.quantity == 0:
        admin.table("cart_items").delete().eq("id", item_id).execute()
    else:
        # Check stock
        prod_resp = admin.table("products").select("stock").eq("id", item_resp.data["product_id"]).single().execute()
        if prod_resp.data.get("stock", 0) < payload.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock.")
        admin.table("cart_items").update({"quantity": payload.quantity}).eq("id", item_id).execute()

    return await get_cart(auth)


@router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(item_id: str, auth: dict = Depends(get_current_user)):
    """Remove a single item from the cart."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        admin.table("cart_items").delete().eq("id", item_id).eq("user_id", user_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not remove item: {str(e)}")

    return await get_cart(auth)


@router.delete("", response_model=MessageResponse)
async def clear_cart(auth: dict = Depends(get_current_user)):
    """Remove all items from the cart."""
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        admin.table("cart_items").delete().eq("user_id", user_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not clear cart: {str(e)}")

    return MessageResponse(message="Cart cleared successfully.")
