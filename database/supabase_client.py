from supabase import create_client, Client
from config import get_settings

_settings = get_settings()

# ── Public client (uses anon key — respects Row Level Security) ────────────────
def get_supabase() -> Client:
    return create_client(_settings.supabase_url, _settings.supabase_anon_key)

# ── Admin client (uses service role key — bypasses RLS, server-side only) ─────
def get_supabase_admin() -> Client:
    return create_client(_settings.supabase_url, _settings.supabase_service_role_key)
