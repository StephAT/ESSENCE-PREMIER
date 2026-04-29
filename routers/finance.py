import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database.supabase_client import get_supabase_admin
from dependencies import get_current_user
from typing import Optional
from pydantic import BaseModel
from datetime import date, timedelta

router = APIRouter(prefix="/finance", tags=["Finance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    order_id: str
    due_days: int = 30
    notes: Optional[str] = None


class InvoicePayment(BaseModel):
    payment_method: str
    paid_date: Optional[date] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _invoice_number() -> str:
    uid = uuid.uuid4().hex[:6].upper()
    return f"INV-{uid}"


# ── Revenue Summary ───────────────────────────────────────────────────────────

@router.get("/summary")
async def finance_summary(auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    orders_resp = (
        admin.table("orders")
        .select("total, status, created_at")
        .eq("user_id", user_id)
        .execute()
    )

    all_orders = orders_resp.data or []
    total_spent = sum(o["total"] for o in all_orders if o["status"] != "cancelled")
    delivered = sum(o["total"] for o in all_orders if o["status"] == "delivered")
    pending_payment = sum(o["total"] for o in all_orders if o["status"] in ("pending", "confirmed"))

    invoices_resp = (
        admin.table("invoices")
        .select("amount, status")
        .eq("user_id", user_id)
        .execute()
    )

    inv_data = invoices_resp.data or []
    unpaid = sum(i["amount"] for i in inv_data if i["status"] == "unpaid")
    overdue = sum(i["amount"] for i in inv_data if i["status"] == "overdue")
    paid = sum(i["amount"] for i in inv_data if i["status"] == "paid")

    return {
        "total_spent": total_spent,
        "delivered_value": delivered,
        "pending_payment": pending_payment,
        "total_orders": len(all_orders),
        "invoices": {
            "unpaid": unpaid,
            "overdue": overdue,
            "paid": paid,
            "total": len(inv_data),
        },
    }


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    query = (
        admin.table("invoices")
        .select("*, orders(reference, status)", count="exact")
        .eq("user_id", user_id)
    )

    if status:
        query = query.eq("status", status)

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"invoices": resp.data, "total": resp.count or len(resp.data), "page": page}


@router.post("/invoices", status_code=201)
async def create_invoice(payload: InvoiceCreate, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # Verify the order belongs to this user
    try:
        order_resp = (
            admin.table("orders")
            .select("id, total, status")
            .eq("id", payload.order_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Order not found.")

    # Check invoice doesn't already exist
    existing = (
        admin.table("invoices")
        .select("id")
        .eq("order_id", payload.order_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Invoice already exists for this order.")

    due = date.today() + timedelta(days=payload.due_days)
    row = {
        "order_id": payload.order_id,
        "user_id": user_id,
        "invoice_number": _invoice_number(),
        "status": "unpaid",
        "amount": order_resp.data["total"],
        "due_date": due.isoformat(),
        "notes": payload.notes,
    }

    try:
        resp = admin.table("invoices").insert(row).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data[0]


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("invoices")
            .select("*, orders(reference, status, delivery_address, created_at)")
            .eq("id", invoice_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    return resp.data


@router.patch("/invoices/{invoice_id}/pay")
async def mark_invoice_paid(
    invoice_id: str,
    payload: InvoicePayment,
    auth: dict = Depends(get_current_user),
):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    paid_on = payload.paid_date.isoformat() if payload.paid_date else date.today().isoformat()

    try:
        resp = (
            admin.table("invoices")
            .update({"status": "paid", "paid_date": paid_on, "payment_method": payload.payment_method})
            .eq("id", invoice_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not resp.data:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    return resp.data[0]


# ── Revenue by period ─────────────────────────────────────────────────────────

@router.get("/revenue")
async def revenue_by_month(auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    resp = (
        admin.table("orders")
        .select("total, status, created_at")
        .eq("user_id", user_id)
        .neq("status", "cancelled")
        .order("created_at", desc=False)
        .execute()
    )

    monthly: dict = {}
    for o in (resp.data or []):
        month = o["created_at"][:7]  # "YYYY-MM"
        monthly[month] = monthly.get(month, 0) + o["total"]

    return [{"month": k, "total": round(v, 2)} for k, v in sorted(monthly.items())]
