from fastapi import APIRouter, HTTPException, Query, Depends
from supabase import Client
from database.supabase_client import get_supabase_admin
from models.schemas import Product, ProductListResponse
from typing import Optional

router = APIRouter(prefix="/products", tags=["Products"])

VALID_CATEGORIES = ["Surgical", "Infusion & IV", "Diagnostic", "PPE", "Lab Supplies"]


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=50, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or SKU"),
    sort_by: Optional[str] = Query("name", description="Sort field: name, price, created_at"),
    order: Optional[str] = Query("asc", description="asc or desc"),
):
    """
    List all active products with pagination, filtering, and search.
    Public endpoint — no authentication required.
    """
    admin = get_supabase_admin()
    query = admin.table("products").select("*", count="exact").eq("is_active", True)

    # Filter by category
    if category and category in VALID_CATEGORIES:
        query = query.eq("category", category)

    # Text search (name or SKU)
    if search:
        query = query.or_(f"name.ilike.%{search}%,sku.ilike.%{search}%")

    # Sort
    valid_sorts = {"name", "price", "created_at"}
    sort_col = sort_by if sort_by in valid_sorts else "name"
    query = query.order(sort_col, desc=(order == "desc"))

    # Pagination
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)

    try:
        resp = query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    products = [Product(**p) for p in resp.data]

    return ProductListResponse(
        products=products,
        total=resp.count or len(products),
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """
    Get a single product by ID. Public endpoint.
    """
    admin = get_supabase_admin()

    try:
        resp = admin.table("products").select("*").eq("id", product_id).eq("is_active", True).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Product not found.")

    return Product(**resp.data)


@router.get("/sku/{sku}", response_model=Product)
async def get_product_by_sku(sku: str):
    """
    Get a single product by SKU. Useful for cart lookups.
    """
    admin = get_supabase_admin()

    try:
        resp = admin.table("products").select("*").eq("sku", sku.upper()).eq("is_active", True).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{sku}' not found.")

    return Product(**resp.data)
