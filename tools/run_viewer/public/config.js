// ============================================================================
// Repro Run Viewer — client config. Edit these, then deploy the public/ folder.
// ============================================================================
//
// SUPABASE_URL / SUPABASE_ANON_KEY:
//   Supabase dashboard > Project Settings > API. The anon key is meant to ship
//   in client code; the repro_runs / repro_events tables are anon READ-ONLY
//   (writes come from the harness with the service_role key). Reusing the same
//   project as the verify_app, so this anon key is the same one.
//
// FULL_LOG_BASE_URL:
//   Public base URL of the Supabase Storage 'repro-logs' bucket. Used for the
//   "Download full log" button. Leave "" if you haven't created the bucket yet.
// ============================================================================

window.APP_CONFIG = {
  SUPABASE_URL: "https://rjnkpoxwdslkgxjliakq.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqbmtwb3h3ZHNsa2d4amxpYWtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwMTQzNTYsImV4cCI6MjA5NjU5MDM1Nn0.-fVclxUX9I5xnY6QudwHQ51P8PTUjDWF5HjFXHhINdU",
  FULL_LOG_BASE_URL: "https://rjnkpoxwdslkgxjliakq.supabase.co/storage/v1/object/public/repro-logs",
};
