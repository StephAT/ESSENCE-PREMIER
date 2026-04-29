-- ============================================================
-- ESSENCE PREMIER — Supabase Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Enable UUID generation
create extension if not exists "pgcrypto";


-- ── 1. PROFILES ──────────────────────────────────────────────
-- Stores extra user info not kept in Supabase Auth
create table if not exists public.profiles (
    id              uuid primary key references auth.users(id) on delete cascade,
    email           text not null,
    first_name      text not null default '',
    last_name       text not null default '',
    facility_name   text not null default '',
    country         text not null default 'Ghana',
    account_type    text not null default 'hospital'
                      check (account_type in ('hospital', 'procurement')),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

-- Auto-update updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.set_updated_at();

-- RLS
alter table public.profiles enable row level security;

create policy "Users can view their own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update their own profile"
  on public.profiles for update
  using (auth.uid() = id);


-- ── 2. PRODUCTS ──────────────────────────────────────────────
create table if not exists public.products (
    id          uuid primary key default gen_random_uuid(),
    sku         text unique not null,
    name        text not null,
    category    text not null
                  check (category in ('Surgical', 'Infusion & IV', 'Diagnostic', 'PPE', 'Lab Supplies')),
    price       numeric(10,2) not null check (price >= 0),
    unit        text not null default 'unit',
    min_order   int not null default 1,
    stock       int not null default 0 check (stock >= 0),
    image_url   text,
    badge       text,
    description text,
    is_active   boolean not null default true,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz
);

create trigger products_updated_at
  before update on public.products
  for each row execute procedure public.set_updated_at();

-- Products are publicly readable; only service role can write
alter table public.products enable row level security;

create policy "Products are publicly readable"
  on public.products for select
  using (true);


-- ── 3. SEED PRODUCTS (your 3 existing catalog items) ─────────
insert into public.products (sku, name, category, price, unit, min_order, stock, image_url, badge, description) values
(
    'EP-SG-7842',
    'Sterile Latex Surgical Gloves',
    'Surgical',
    48.00,
    'box of 50 pairs',
    10,
    500,
    'images/Sterile Latex Surgical Gloves.webp',
    'Bestseller',
    'Premium sterile latex surgical gloves. Powder-free, ambidextrous. FDA cleared, ISO 13485 certified. Supplied in boxes of 50 pairs.'
),
(
    'EP-IV-2291',
    'Disposable IV Infusion Set with Filter',
    'Infusion & IV',
    120.00,
    'pack of 100',
    1,
    300,
    'images/Infusion Disposable IV Infusion Set.jfif',
    'Certified',
    'Single-use IV infusion set with inline 15-micron filter. Luer lock connector, 150cm tubing. CE marked and ISO 10555 compliant.'
),
(
    'EP-PPE-0041',
    'N95 Respirator Mask',
    'PPE',
    36.00,
    'box of 20',
    5,
    800,
    'images/N95 Respirator Mask.webp',
    'New',
    'NIOSH-approved N95 filtering facepiece respirator. ≥95% filtration efficiency. Individually wrapped. Suitable for clinical environments.'
)
on conflict (sku) do nothing;


-- ── 4. CART ITEMS ────────────────────────────────────────────
create table if not exists public.cart_items (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    product_id  uuid not null references public.products(id) on delete cascade,
    quantity    int not null default 1 check (quantity > 0),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz,
    unique (user_id, product_id)
);

create trigger cart_items_updated_at
  before update on public.cart_items
  for each row execute procedure public.set_updated_at();

alter table public.cart_items enable row level security;

create policy "Users can manage their own cart"
  on public.cart_items for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);


-- ── 5. ORDERS ────────────────────────────────────────────────
create table if not exists public.orders (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references auth.users(id) on delete restrict,
    reference           text unique not null,
    status              text not null default 'pending'
                          check (status in ('pending','confirmed','processing','shipped','delivered','cancelled')),
    subtotal            numeric(12,2) not null,
    vat_amount          numeric(12,2) not null default 0,
    delivery_fee        numeric(10,2) not null default 0,
    total               numeric(12,2) not null,
    delivery_option     text not null default 'standard',
    payment_method      text not null default 'card',
    delivery_address    jsonb not null,
    notes               text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz
);

create trigger orders_updated_at
  before update on public.orders
  for each row execute procedure public.set_updated_at();

alter table public.orders enable row level security;

create policy "Users can view their own orders"
  on public.orders for select
  using (auth.uid() = user_id);

create policy "Users can insert their own orders"
  on public.orders for insert
  with check (auth.uid() = user_id);


-- ── 6. ORDER ITEMS ───────────────────────────────────────────
create table if not exists public.order_items (
    id          uuid primary key default gen_random_uuid(),
    order_id    uuid not null references public.orders(id) on delete cascade,
    product_id  uuid not null references public.products(id) on delete restrict,
    sku         text not null,
    name        text not null,
    quantity    int not null check (quantity > 0),
    unit_price  numeric(10,2) not null,
    subtotal    numeric(12,2) not null,
    image_url   text,
    created_at  timestamptz not null default now()
);

alter table public.order_items enable row level security;

create policy "Users can view their own order items"
  on public.order_items for select
  using (
    exists (
      select 1 from public.orders
      where orders.id = order_items.order_id
        and orders.user_id = auth.uid()
    )
  );


-- ── 7. INDEXES ───────────────────────────────────────────────
create index if not exists idx_products_category  on public.products(category);
create index if not exists idx_products_sku        on public.products(sku);
create index if not exists idx_products_is_active  on public.products(is_active);
create index if not exists idx_cart_user           on public.cart_items(user_id);
create index if not exists idx_orders_user         on public.orders(user_id);
create index if not exists idx_order_items_order   on public.order_items(order_id);
