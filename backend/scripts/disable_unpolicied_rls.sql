-- ============================================================================
-- Fix Supabase's default "RLS enabled but NO policy" on public tables.
-- ----------------------------------------------------------------------------
-- Supabase turns rowsecurity ON for every public table. With no policy, a
-- NON-bypass role (app_user) is denied ALL rows -> login + every read breaks.
-- The old `postgres` role hid this because it has BYPASSRLS.
--
-- Gradual-rollout rule: a table is EITHER
--   (a) RLS OFF  -> not migrated yet, app sees everything (app-layer filter), OR
--   (b) RLS ON + tenant policy -> migrated & isolated (e.g. announcements).
--
-- This script disables RLS on every public table that has RLS on but NO policy,
-- so it leaves already-migrated tables (announcements) untouched. As we migrate
-- each table later, its migration re-enables RLS + adds the tenant policy.
--
-- Run in the Supabase SQL editor (it runs as `postgres`, the table owner).
-- Idempotent + safe to re-run.
-- ============================================================================

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'                 -- ordinary tables only
          AND c.relrowsecurity = true         -- RLS currently enabled
          AND NOT EXISTS (                    -- ...but no policy defined
              SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid
          )
        ORDER BY c.relname
    LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', r.relname);
        RAISE NOTICE 'RLS disabled on public.%', r.relname;
    END LOOP;
END$$;

-- Verify: announcements should stay ON (it has a policy); the rest OFF.
SELECT c.relname AS table_name,
       c.relrowsecurity AS rls_on,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relrowsecurity DESC, c.relname;
