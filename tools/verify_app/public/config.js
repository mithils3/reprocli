// ============================================================================
// EDIT THESE FOUR VALUES, then deploy. Nothing else needs touching.
// ============================================================================
//
// 1. SUPABASE_URL / SUPABASE_ANON_KEY:
//      Supabase dashboard > Project Settings > API.
//      The anon (public) key is meant to live in client code; it is gated by
//      the Row Level Security policies in supabase_schema.sql.
//
// 2. ADMIN_NAMES:
//      Reviewers whose typed name matches (case-insensitive) get the admin
//      Dashboard tab. Put your name here.
//
// 3. TRACE_BASE_URL:
//      Public base URL of the Supabase Storage 'traces' bucket, e.g.
//      https://YOURPROJECT.supabase.co/storage/v1/object/public/traces
//      Leave "" if you have not uploaded traces yet — the app still works,
//      it just hides the "show model trace" button.
// ============================================================================

window.APP_CONFIG = {
  SUPABASE_URL: "https://rjnkpoxwdslkgxjliakq.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqbmtwb3h3ZHNsa2d4amxpYWtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwMTQzNTYsImV4cCI6MjA5NjU5MDM1Nn0.-fVclxUX9I5xnY6QudwHQ51P8PTUjDWF5HjFXHhINdU",
  ADMIN_NAMES: ["mithil"],
  TRACE_BASE_URL: "https://rjnkpoxwdslkgxjliakq.supabase.co/storage/v1/object/public/traces",
};
