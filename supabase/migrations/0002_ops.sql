-- Operations tables: orders, shipments, supplier prices, live listings, alerts and daily shop figures.
-- Run AFTER 0001_init.sql, in the Supabase SQL Editor. Safe to run again. No customer personal data: order IDs and tracking numbers only.

-- ============================================================ orders
create table if not exists public.orders (
  id                text primary key check (id ~ '^[A-Za-z0-9_-]{3,40}$'),
  order_date        date not null,
  channel           text not null check (channel in ('ebay-uk', 'social', 'shopify')),
  product_id        text,
  title             text not null default '' check (not public.looks_like_email(title)),
  qty               integer not null default 1 check (qty > 0),
  revenue_gbp       numeric(10, 2) not null default 0,
  item_cost_gbp     numeric(10, 2) not null default 0,
  shipping_cost_gbp numeric(10, 2) not null default 0,
  fees_gbp          numeric(10, 2) not null default 0,
  refund_gbp        numeric(10, 2) not null default 0,
  status            text not null default 'new' check (status in ('new', 'ordered', 'shipped', 'delivered', 'cancelled', 'refunded')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index if not exists orders_date_idx on public.orders (order_date desc);
drop trigger if exists orders_touch on public.orders;
create trigger orders_touch before update on public.orders for each row execute function public.touch_updated_at();
alter table public.orders enable row level security;

-- ============================================================ shipments
create table if not exists public.shipments (
  id              text primary key,
  order_id        text references public.orders (id) on delete cascade,
  supplier        text not null default '',
  carrier         text not null default '',
  tracking_no     text not null default '' check (tracking_no !~ '\s'),
  shipped_date    date,
  promised_days   integer not null default 5 check (promised_days between 1 and 60),
  expected_by     date generated always as (shipped_date + promised_days) stored,
  status          text not null default 'pending' check (status in ('pending', 'in_transit', 'out_for_delivery', 'delivered', 'exception', 'returned')),
  last_event      text not null default '' check (not public.looks_like_email(last_event)),
  last_event_at   timestamptz,
  last_checked_at timestamptz,
  delivered_date  date,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists shipments_status_idx on public.shipments (status, shipped_date);
drop trigger if exists shipments_touch on public.shipments;
create trigger shipments_touch before update on public.shipments for each row execute function public.touch_updated_at();
alter table public.shipments enable row level security;

-- ============================================================ live listings and supplier prices
create table if not exists public.listings (
  product_id          text primary key,
  title               text not null default '' check (not public.looks_like_email(title)),
  channel             text not null check (channel in ('ebay-uk', 'social', 'shopify')),
  price_gbp           numeric(10, 2) not null,
  assumed_cost_gbp    numeric(10, 2) not null,
  assumed_shipping_gbp numeric(10, 2) not null default 0,
  fulfilment_model    text not null default 'hold_stock' check (fulfilment_model in ('hold_stock', 'wholesale_dropship', 'marketplace_dropship')),
  postage_gbp         numeric(10, 2) not null default 0,
  active              boolean not null default true,
  updated_at          timestamptz not null default now()
);
alter table public.listings enable row level security;

create table if not exists public.supplier_prices (
  id           bigint generated always as identity primary key,
  product_id   text not null,
  checked_date date not null,
  cost_gbp     numeric(10, 2) not null,
  shipping_gbp numeric(10, 2) not null default 0,
  source       text not null default 'import',
  unique (product_id, checked_date, source)
);
create index if not exists supplier_prices_idx on public.supplier_prices (product_id, checked_date desc);
alter table public.supplier_prices enable row level security;

-- ============================================================ alerts (what needs you)
create table if not exists public.alerts (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  kind       text not null,
  severity   text not null check (severity in ('info', 'warning', 'critical')),
  entity     text not null,
  entity_id  text not null,
  message    text not null check (not public.looks_like_email(message)),
  status     text not null default 'open' check (status in ('open', 'acknowledged', 'closed')),
  dedupe_key text not null unique
);
create index if not exists alerts_status_idx on public.alerts (status, severity);
drop trigger if exists alerts_touch on public.alerts;
create trigger alerts_touch before update on public.alerts for each row execute function public.touch_updated_at();
alter table public.alerts enable row level security;

-- ============================================================ daily shop figures (from Shopify or a manual export)
create table if not exists public.shop_daily (
  day                 date not null,
  channel             text not null check (channel in ('ebay-uk', 'social', 'shopify')),
  sessions            integer not null default 0,
  carts               integer not null default 0,
  checkouts           integer not null default 0,
  orders              integer not null default 0,
  abandoned_checkouts integer not null default 0,
  revenue_gbp         numeric(10, 2) not null default 0,
  primary key (day, channel)
);
alter table public.shop_daily enable row level security;

-- ============================================================ social metrics from platform exports: tell posts apart by their reference
alter table public.social_metrics add column if not exists post_ref text not null default '';
drop index if exists public.social_metrics_unique;
create unique index if not exists social_metrics_unique2 on public.social_metrics
  (platform, post_ref, coalesce(post_id::text, ''), coalesce(campaign_id::text, ''), metric_date, source);

-- ============================================================ messages keep their triage details (tier, template, missing facts)
alter table public.messages add column if not exists meta jsonb not null default '{}'::jsonb;

-- ============================================================ Pinterest joins the customer-care channels
alter table public.conversations drop constraint if exists conversations_channel_check;
alter table public.conversations add constraint conversations_channel_check
  check (channel in ('ebay', 'facebook', 'instagram', 'tiktok', 'whatsapp', 'youtube', 'x', 'pinterest', 'other'));

-- ============================================================ access: owner only, as in 0001
revoke all on public.orders, public.shipments, public.listings, public.supplier_prices, public.alerts, public.shop_daily from anon, authenticated;
grant all on public.orders, public.shipments, public.listings, public.supplier_prices, public.alerts, public.shop_daily to service_role;
grant usage on all sequences in schema public to service_role;
grant select on public.orders, public.shipments, public.listings, public.supplier_prices, public.alerts, public.shop_daily to authenticated;
grant update (status) on public.alerts to authenticated;   -- you can acknowledge or close an alert; nothing else is editable from the dashboard
grant usage on all sequences in schema public to authenticated;

do $$
declare t text;
begin
  foreach t in array array['orders', 'shipments', 'listings', 'supplier_prices', 'alerts', 'shop_daily'] loop
    execute format('drop policy if exists owner_read on public.%I', t);
    execute format('create policy owner_read on public.%I for select to authenticated using (public.is_owner())', t);
  end loop;
end $$;
drop policy if exists owner_update on public.alerts;
create policy owner_update on public.alerts for update to authenticated using (public.is_owner()) with check (public.is_owner());

do $$
declare t text;
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    foreach t in array array['alerts', 'shipments', 'orders'] loop
      begin
        execute format('alter publication supabase_realtime add table public.%I', t);
      exception when duplicate_object then null;
      end;
    end loop;
  end if;
end $$;
