from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Auth ──────────────────────────────────────────────────────────────────────

class AccountType(str, Enum):
    hospital = "hospital"
    procurement = "procurement"


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    facility_name: str
    country: str = "Ghana"
    account_type: AccountType = AccountType.hospital

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    first_name: str
    last_name: str
    facility_name: str


class UserProfile(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    facility_name: str
    country: str
    account_type: str
    created_at: datetime


# ── Products ─────────────────────────────────────────────────────────────────

class ProductCategory(str, Enum):
    surgical = "Surgical"
    infusion = "Infusion & IV"
    diagnostic = "Diagnostic"
    ppe = "PPE"
    lab = "Lab Supplies"


class Product(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    price: float
    unit: str
    min_order: int = 1
    stock: int
    image_url: Optional[str] = None
    badge: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class ProductListResponse(BaseModel):
    products: List[Product]
    total: int
    page: int
    page_size: int


# ── Cart ─────────────────────────────────────────────────────────────────────

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CartItemUpdate(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def qty_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v


class CartItem(BaseModel):
    id: str
    product_id: str
    sku: str
    name: str
    price: float
    unit: str
    quantity: int
    subtotal: float
    image_url: Optional[str] = None


class CartResponse(BaseModel):
    items: List[CartItem]
    item_count: int
    subtotal: float
    vat_rate: float = 0.15
    vat_amount: float
    total: float


# ── Orders ────────────────────────────────────────────────────────────────────

class PaymentMethod(str, Enum):
    card = "card"
    bank_transfer = "bank_transfer"
    net30 = "net_30"
    net60 = "net_60"
    mobile_money = "mobile_money"


class DeliveryOption(str, Enum):
    standard = "standard"
    express = "express"
    same_day = "same_day"


class DeliveryAddress(BaseModel):
    full_name: str
    hospital_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    region: str
    country: str = "Ghana"
    phone: str


class CheckoutRequest(BaseModel):
    delivery_address: DeliveryAddress
    delivery_option: DeliveryOption = DeliveryOption.standard
    payment_method: PaymentMethod = PaymentMethod.card
    notes: Optional[str] = None


class OrderItem(BaseModel):
    product_id: str
    sku: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float
    image_url: Optional[str] = None


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class Order(BaseModel):
    id: str
    reference: str
    status: OrderStatus
    items: List[OrderItem]
    subtotal: float
    vat_amount: float
    delivery_fee: float
    total: float
    delivery_option: str
    payment_method: str
    delivery_address: dict
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class OrderListItem(BaseModel):
    id: str
    reference: str
    status: OrderStatus
    item_count: int
    total: float
    created_at: datetime


# ── Shared ────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True
