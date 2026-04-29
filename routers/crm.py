import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database.supabase_client import get_supabase_admin
from dependencies import get_current_user
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/crm", tags=["CRM"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    title: Optional[str] = None
    organization: str
    email: Optional[str] = None
    phone: Optional[str] = None
    type: str = "client"
    region: Optional[str] = None
    country: str = "Ghana"
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    type: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None


class InteractionCreate(BaseModel):
    type: str = "note"
    subject: str
    notes: Optional[str] = None
    outcome: Optional[str] = None
    next_action: Optional[str] = None
    interaction_date: Optional[datetime] = None


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.get("/contacts")
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    auth: dict = Depends(get_current_user),
):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    query = (
        admin.table("crm_contacts")
        .select("*", count="exact")
        .eq("owner_id", user_id)
    )

    if type:
        query = query.eq("type", type)
    if search:
        query = query.or_(
            f"first_name.ilike.%{search}%,last_name.ilike.%{search}%,organization.ilike.%{search}%,email.ilike.%{search}%"
        )

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"contacts": resp.data, "total": resp.count or len(resp.data), "page": page, "page_size": page_size}


@router.post("/contacts", status_code=201)
async def create_contact(payload: ContactCreate, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    valid_types = {"client", "prospect", "partner", "supplier"}
    if payload.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"type must be one of {valid_types}")

    row = {**payload.model_dump(), "owner_id": user_id}

    try:
        resp = admin.table("crm_contacts").insert(row).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data[0]


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        resp = (
            admin.table("crm_contacts")
            .select("*")
            .eq("id", contact_id)
            .eq("owner_id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Contact not found.")

    return resp.data


@router.patch("/contacts/{contact_id}")
async def update_contact(contact_id: str, payload: ContactUpdate, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    try:
        resp = (
            admin.table("crm_contacts")
            .update(updates)
            .eq("id", contact_id)
            .eq("owner_id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not resp.data:
        raise HTTPException(status_code=404, detail="Contact not found.")

    return resp.data[0]


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    try:
        admin.table("crm_contacts").delete().eq("id", contact_id).eq("owner_id", user_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Interactions ──────────────────────────────────────────────────────────────

@router.get("/contacts/{contact_id}/interactions")
async def list_interactions(contact_id: str, auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # Verify ownership
    try:
        admin.table("crm_contacts").select("id").eq("id", contact_id).eq("owner_id", user_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Contact not found.")

    try:
        resp = (
            admin.table("crm_interactions")
            .select("*")
            .eq("contact_id", contact_id)
            .order("interaction_date", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data


@router.post("/contacts/{contact_id}/interactions", status_code=201)
async def log_interaction(
    contact_id: str,
    payload: InteractionCreate,
    auth: dict = Depends(get_current_user),
):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    # Verify ownership
    try:
        admin.table("crm_contacts").select("id").eq("id", contact_id).eq("owner_id", user_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Contact not found.")

    row = {
        **payload.model_dump(),
        "contact_id": contact_id,
        "user_id": user_id,
    }
    if row.get("interaction_date"):
        row["interaction_date"] = row["interaction_date"].isoformat()

    try:
        resp = admin.table("crm_interactions").insert(row).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return resp.data[0]


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
async def crm_summary(auth: dict = Depends(get_current_user)):
    user_id = auth["user"].id
    admin = get_supabase_admin()

    contacts_resp = (
        admin.table("crm_contacts")
        .select("type", count="exact")
        .eq("owner_id", user_id)
        .execute()
    )

    by_type = {"client": 0, "prospect": 0, "partner": 0, "supplier": 0}
    for row in (contacts_resp.data or []):
        t = row.get("type", "client")
        by_type[t] = by_type.get(t, 0) + 1

    interactions_resp = (
        admin.table("crm_interactions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )

    return {
        "total_contacts": contacts_resp.count or 0,
        "by_type": by_type,
        "total_interactions": interactions_resp.count or 0,
    }
