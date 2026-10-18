# Smart Movie Hub — database setup

The app supports persistent Watchlists with Supabase. If Supabase secrets are not configured, signed-in users fall back to local JSON files; local files may be ephemeral on hosted platforms.

## 1. Create the table in Supabase

Open the Supabase project SQL Editor and run:

```sql
create table if not exists public.movie_watchlists (
  user_email text primary key,
  items jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create or replace function public.set_movie_watchlists_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists movie_watchlists_updated_at on public.movie_watchlists;
create trigger movie_watchlists_updated_at
before update on public.movie_watchlists
for each row execute function public.set_movie_watchlists_updated_at();
```

## 2. Add Streamlit secrets

In local development, create `.streamlit/secrets.toml` (do not commit it):

```toml
TMDB_API_KEY = "your_tmdb_api_key"
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your_supabase_service_role_key"
```

For Streamlit Community Cloud, add the same values in **App settings → Secrets**. Keep the service-role key secret and never place it in frontend code or a public repository. The app uses it only on the server, after Google sign-in, to query rows by the authenticated account email.

## 3. Authentication and deployment notes

- Configure Google sign-in in Streamlit and verify that the identity provider returns a verified email.
- The current table is accessed by the app server using the Supabase service-role key. Do not expose that key to clients or commit it. If you later move database access to a browser/client, replace this approach with Supabase Auth and row-level security policies tied to the authenticated user ID.
- Back up the table periodically. The Watchlist is stored as JSON in the `items` column; each item can include movie metadata, status, personal rating, and a note.
- If Supabase is not configured, the app remains usable and falls back to local JSON storage.
