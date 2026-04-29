-- ============================================================
-- ESSENCE PREMIER — Migration 002
-- CRM, Finance, Supply Chain tables
-- Run in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- ── 1. SUPPLIERS ─────────────────────────────────────────────
create table if not exists public.suppliers (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    contact_person  text,
    email           text,
    phone           text,
    country         text not null default 'Ghana',
    address         text,
    category        text,
    rating          numeric(3,1) check (rating between 1 and 5),
    is_active       boolean not null default true,
    notes           text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

create trigger suppliers_updated_at
  before update on public.suppliers
  for each row execute procedure public.set_updated_at();

alter table public.suppliers enable row level security;
create policy "Authenticated users can manage suppliers"
  on public.suppliers for all
  using (auth.uid() is not null)
  with check (auth.uid() is not null);


-- ── 2. SUPPLIER PRODUCTS ─────────────────────────────────────
create table if not exists public.supplier_products (
    id              uuid primary key default gen_random_uuid(),
    supplier_id     uuid not null references public.suppliers(id) on delete cascade,
    product_id      uuid not null references public.products(id) on delete cascade,
    unit_cost       numeric(10,2) not null,
    lead_time_days  int not null default 7,
    is_preferred    boolean not null default false,
    created_at      timestamptz not null default now(),
    unique(supplier_id, product_id)
);

alter table public.supplier_products enable row level security;
create policy "Authenticated users can manage supplier_products"
  on public.supplier_products for all
  using (auth.uid() is not null)
  with check (auth.uid() is not null);


-- ── 3. PURCHASE ORDERS (restock orders to suppliers) ─────────
create table if not exists public.purchase_orders (
    id              uuid primary key default gen_random_uuid(),
    supplier_id     uuid not null references public.suppliers(id),
    reference       text unique not null,
    status          text not null default 'draft'
                      check (status in ('draft','sent','confirmed','shipped','received','cancelled')),
    total_amount    numeric(12,2) not null default 0,
    expected_date   date,
    received_date   date,
    notes           text,
    created_by      uuid references auth.users(id),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

create trigger purchase_orders_updated_at
  before update on public.purchase_orders
  for each row execute procedure public.set_updated_at();

alter table public.purchase_orders enable row level security;
create policy "Authenticated users can manage purchase_orders"
  on public.purchase_orders for all
  using (auth.uid() is not null)
  with check (auth.uid() is not null);


-- ── 4. PURCHASE ORDER ITEMS ───────────────────────────────────
create table if not exists public.purchase_order_items (
    id                  uuid primary key default gen_random_uuid(),
    purchase_order_id   uuid not null references public.purchase_orders(id) on delete cascade,
    product_id          uuid not null references public.products(id),
    product_name        text not null,
    product_sku         text not null,
    quantity            int not null check (quantity > 0),
    unit_cost           numeric(10,2) not null,
    subtotal            numeric(12,2) not null,
    created_at          timestamptz not null default now()
);

alter table public.purchase_order_items enable row level security;
create policy "Authenticated users can manage purchase_order_items"
  on public.purchase_order_items for all
  using (auth.uid() is not null)
  with check (auth.uid() is not null);


-- ── 5. DISTRIBUTION PARTNERS ──────────────────────────────────
create table if not exists public.partners (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    type            text not null default 'distributor'
                      check (type in ('distributor','logistics','warehouse','agent')),
    contact_person  text,
    email           text,
    phone           text,
    region          text,
    country         text not null default 'Ghana',
    is_active       boolean not null default true,
    notes           text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

create trigger partners_updated_at
  before update on public.partners
  for each row execute procedure public.set_updated_at();

alter table public.partners enable row level security;
create policy "Authenticated users can manage partners"
  on public.partners for all
  using (auth.uid() is not null)
  with check (auth.uid() is not null);


-- ── 6. CRM CONTACTS ───────────────────────────────────────────
create table if not exists public.crm_contacts (
    id              uuid primary key default gen_random_uuid(),
    owner_id        uuid not null references auth.users(id),
    first_name      text not null,
    last_name       text not null,
    title           text,
    organization    text not null,
    email           text,
    phone           text,
    type            text not null default 'client'
                      check (type in ('client','prospect','partner','supplier')),
    region          text,
    country         text not null default 'Ghana',
    notes           text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

create trigger crm_contacts_updated_at
  before update on public.crm_contacts
  for each row execute procedure public.set_updated_at();

alter table public.crm_contacts enable row level security;
create policy "Users can manage their own CRM contacts"
  on public.crm_contacts for all
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);


-- ── 7. CRM INTERACTIONS ───────────────────────────────────────
create table if not exists public.crm_interactions (
    id                  uuid primary key default gen_random_uuid(),
    contact_id          uuid not null references public.crm_contacts(id) on delete cascade,
    user_id             uuid not null references auth.users(id),
    type                text not null default 'note'
                          check (type in ('call','email','meeting','note','follow_up')),
    subject             text not null,
    notes               text,
    outcome             text,
    next_action         text,
    interaction_date    timestamptz not null default now(),
    created_at          timestamptz not null default now()
);

alter table public.crm_interactions enable row level security;
create policy "Users can manage their own interactions"
  on public.crm_interactions for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);


-- ── 8. INVOICES ───────────────────────────────────────────────
create table if not exists public.invoices (
    id              uuid primary key default gen_random_uuid(),
    order_id        uuid not null references public.orders(id),
    user_id         uuid not null references auth.users(id),
    invoice_number  text unique not null,
    status          text not null default 'unpaid'
                      check (status in ('unpaid','paid','overdue','cancelled')),
    amount          numeric(12,2) not null,
    due_date        date not null,
    paid_date       date,
    payment_method  text,
    notes           text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz
);

create trigger invoices_updated_at
  before update on public.invoices
  for each row execute procedure public.set_updated_at();

alter table public.invoices enable row level security;
create policy "Users can view their own invoices"
  on public.invoices for select
  using (auth.uid() = user_id);
create policy "Users can insert their own invoices"
  on public.invoices for insert
  with check (auth.uid() = user_id);
create policy "Users can update their own invoices"
  on public.invoices for update
  using (auth.uid() = user_id);


-- ── 9. INDEXES ────────────────────────────────────────────────
create index if not exists idx_suppliers_active        on public.suppliers(is_active);
create index if not exists idx_purchase_orders_supplier on public.purchase_orders(supplier_id);
create index if not exists idx_purchase_orders_status   on public.purchase_orders(status);
create index if not exists idx_crm_contacts_owner       on public.crm_contacts(owner_id);
create index if not exists idx_crm_contacts_type        on public.crm_contacts(type);
create index if not exists idx_crm_interactions_contact on public.crm_interactions(contact_id);
create index if not exists idx_invoices_user            on public.invoices(user_id);
create index if not exists idx_invoices_status          on public.invoices(status);
create index if not exists idx_partners_active          on public.partners(is_active);


-- ── 10. SEED DATA ─────────────────────────────────────────────

-- Seed suppliers
insert into public.suppliers (name, contact_person, email, phone, country, address, category, rating, notes) values
('Medline West Africa Ltd', 'Kwame Asante', 'kwame@medlinewestafrica.com', '+233-24-100-2000', 'Ghana', '14 Ring Road Central, Accra', 'Surgical', 4.5, 'Primary supplier for surgical consumables. ISO 13485 certified.'),
('Cardinal Health Ghana', 'Abena Mensah', 'abena@cardinalgh.com', '+233-30-277-8800', 'Ghana', '7 Commerce Drive, Tema', 'Infusion & IV', 4.2, 'Key IV and infusion product supplier. Strong delivery record.'),
('3M Safety West Africa', 'Kofi Boateng', 'kofi@3mwestafrica.com', '+233-24-555-7700', 'Ghana', 'Airport City, Accra', 'PPE', 4.8, 'Exclusive N95 supplier. NIOSH-approved products only.')
on conflict do nothing;

-- Seed distribution partners
insert into public.partners (name, type, contact_person, email, phone, region, country, notes) values
('GhanaExpress Medical Logistics', 'logistics', 'Yaw Darko', 'yaw@ghanaexpress.com', '+233-24-333-4400', 'Greater Accra', 'Ghana', 'Same-day delivery partner for Accra Metro area.'),
('Volta Medical Distribution', 'distributor', 'Ama Owusu', 'ama@voltamed.com', '+233-36-200-1100', 'Volta Region', 'Ghana', 'Covers Volta and Oti regions. Reliable weekly routes.'),
('MedStore Ashanti Hub', 'warehouse', 'Nana Osei', 'nana@medstoregh.com', '+233-32-205-5500', 'Ashanti Region', 'Ghana', 'Bonded warehouse partner in Kumasi.')
on conflict do nothing;
