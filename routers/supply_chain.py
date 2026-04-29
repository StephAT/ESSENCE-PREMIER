import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database.supabase_client import get_supabase_admin
from dependencies import get_current_user
from typing import Optional, List
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/supply-chain", tags=["Supply Chain"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: str = "Ghana"
    address: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PartnerCreate(BaseModel):
    name: str
    type: str = "distributor"
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    country: str = "Ghana"
    notes: Optional[str] = None


class PurchaseOrderItem(BaseModel):
    product_id: str
    quantity: int
    unit_cost: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    items: List[PurchaseOrderItem]
    expected_date: Optional[date] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _po_reference() -> str:
    uid = uuid.uuid4().hex[:8].upper()
    return f"PO-{uid[:4]}-{uid[4:]}"


# ── Suppliers ─────────────────────────────────────────────────────────────────

@router.get("/suppliers")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
):
    admin = get_supabase_admin()
    query = admin.table("suppliers").select("*", count="exact")

    if active_only:
        query = query.eq("is_active", True)
    if search:
        query = query.or_(f"name.ilike.%{search}%,category.ilike.%{search}%")

    offset = (page - 1) * page_size
    query = query.order("name").range(offset, offset + page_size - 1)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"suppliers": resp.data, "total": resp.count or len(resp.data)}


@router.post("/suppliers", status_code=201)
async def create_supplier(payload: SupplierCreate, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()

    try:
        resp = admin.table("suppliers").insert(payload.model_dump()).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data[0]


@router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()

    try:
        resp = admin.table("suppliers").select("*").eq("id", supplier_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    return resp.data


@router.patch("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, payload: SupplierUpdate, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    try:
        resp = admin.table("suppliers").update(updates).eq("id", supplier_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not resp.data:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    return resp.data[0]


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def deactivate_supplier(supplier_id: str, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    try:
        admin.table("suppliers").update({"is_active": False}).eq("id", supplier_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Purchase Orders ───────────────────────────────────────────────────────────

@router.get("/purchase-orders")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
):
    admin = get_supabase_admin()
    query = admin.table("purchase_orders").select("*, suppliers(name)", count="exact")

    if status:
        query = query.eq("status", status)

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"purchase_orders": resp.data, "total": resp.count or len(resp.data)}


@router.post("/purchase-orders", status_code=201)
async def create_purchase_order(payload: PurchaseOrderCreate, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required.")

    # Fetch product names/SKUs
    product_ids = [i.product_id for i in payload.items]
    products_resp = (
        admin.table("products")
        .select("id, name, sku")
        .in_("id", product_ids)
        .execute()
    )
    products_map = {p["id"]: p for p in (products_resp.data or [])}

    total_amount = sum(i.quantity * i.unit_cost for i in payload.items)

    # Create PO header
    po_row = {
        "supplier_id": payload.supplier_id,
        "reference": _po_reference(),
        "status": "draft",
        "total_amount": round(total_amount, 2),
        "expected_date": payload.expected_date.isoformat() if payload.expected_date else None,
        "notes": payload.notes,
        "created_by": user_id,
    }

    try:
        po_resp = admin.table("purchase_orders").insert(po_row).execute()
        po_id = po_resp.data[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Create PO items
    items_rows = []
    for item in payload.items:
        prod = products_map.get(item.product_id, {})
        items_rows.append({
            "purchase_order_id": po_id,
            "product_id": item.product_id,
            "product_name": prod.get("name", "Unknown"),
            "product_sku": prod.get("sku", ""),
            "quantity": item.quantity,
            "unit_cost": item.unit_cost,
            "subtotal": round(item.quantity * item.unit_cost, 2),
        })

    try:
        admin.table("purchase_order_items").insert(items_rows).execute()
    except Exception as e:
        admin.table("purchase_orders").delete().eq("id", po_id).execute()
        raise HTTPException(status_code=500, detail="Failed to save PO items.")

    return {**po_resp.data[0], "items": items_rows}


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(po_id: str, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("purchase_orders")
            .select("*, suppliers(*), purchase_order_items(*)")
            .eq("id", po_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Purchase order not found.")

    return resp.data


@router.patch("/purchase-orders/{po_id}/status")
async def update_po_status(po_id: str, status: str, auth: dict = Depends(get_current_user)):
    valid = {"draft", "sent", "confirmed", "shipped", "received", "cancelled"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")

    admin = get_supabase_admin()
    updates = {"status": status}

    if status == "received":
        # Update product stock levels when PO is received
        try:
            items_resp = (
                admin.table("purchase_order_items")
                .select("product_id, quantity")
                .eq("purchase_order_id", po_id)
                .execute()
            )
            for item in (items_resp.data or []):
                prod_resp = (
                    admin.table("products")
                    .select("stock")
                    .eq("id", item["product_id"])
                    .single()
                    .execute()
                )
                new_stock = prod_resp.data["stock"] + item["quantity"]
                admin.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()
        except Exception:
            pass  # Best-effort stock update

    try:
        resp = admin.table("purchase_orders").update(updates).eq("id", po_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not resp.data:
        raise HTTPException(status_code=404, detail="Purchase order not found.")

    return resp.data[0]


# ── Partners ──────────────────────────────────────────────────────────────────

@router.get("/partners")
async def list_partners(
    active_only: bool = Query(True),
    auth: dict = Depends(get_current_user),
):
    admin = get_supabase_admin()
    query = admin.table("partners").select("*")
    if active_only:
        query = query.eq("is_active", True)
    query = query.order("name")

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data


@router.post("/partners", status_code=201)
async def create_partner(payload: PartnerCreate, auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()
    valid_types = {"distributor", "logistics", "warehouse", "agent"}
    if payload.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"type must be one of {valid_types}")

    try:
        resp = admin.table("partners").insert(payload.model_dump()).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data[0]


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
async def supply_chain_summary(auth: dict = Depends(get_current_user)):
    admin = get_supabase_admin()

    suppliers_resp = admin.table("suppliers").select("id", count="exact").eq("is_active", True).execute()
    partners_resp = admin.table("partners").select("id", count="exact").eq("is_active", True).execute()
    po_resp = admin.table("purchase_orders").select("status, total_amount").execute()

    po_data = po_resp.data or []
    po_by_status = {}
    po_total_value = 0
    for po in po_data:
        s = po["status"]
        po_by_status[s] = po_by_status.get(s, 0) + 1
        po_total_value += po.get("total_amount", 0)

    return {
        "active_suppliers": suppliers_resp.count or 0,
        "active_partners": partners_resp.count or 0,
        "purchase_orders": {
            "total": len(po_data),
            "by_status": po_by_status,
            "total_value": round(po_total_value, 2),
        },
    }
