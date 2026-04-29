from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import get_settings
from routers import auth, products, cart, orders
from routers import crm, finance, supply_chain

settings = get_settings()

app = FastAPI(
    title="ESSENCE PREMIER API",
    description=(
        "Backend API for ESSENCE PREMIER — Africa's trusted medical procurement platform. "
        "Covers Web Selling, CRM, Finance Management, Ordering, and Supply Chain Management."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1")
app.include_router(products.router,     prefix="/api/v1")
app.include_router(cart.router,         prefix="/api/v1")
app.include_router(orders.router,       prefix="/api/v1")
app.include_router(crm.router,          prefix="/api/v1")
app.include_router(finance.router,      prefix="/api/v1")
app.include_router(supply_chain.router, prefix="/api/v1")

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "ESSENCE PREMIER API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "modules": [
            "Web Selling",
            "CRM",
            "Finance Management",
            "Ordering System",
            "Supply Chain Management",
        ],
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
