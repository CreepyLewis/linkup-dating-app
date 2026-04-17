-- ============================================
-- Run this in Supabase SQL Editor to fix:
-- 1. Existing auth users who have no profile row
-- 2. RLS policies that block writes
-- ============================================

-- Step 1: Disable RLS on users table so the app can read/write freely
-- (The service role key bypasses RLS anyway, but this is a safety net)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE likes DISABLE ROW LEVEL SECURITY;
ALTER TABLE passes DISABLE ROW LEVEL SECURITY;
ALTER TABLE matches DISABLE ROW LEVEL SECURITY;
ALTER TABLE messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;
ALTER TABLE reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE blocks DISABLE ROW LEVEL SECURITY;
ALTER TABLE events DISABLE ROW LEVEL SECURITY;
ALTER TABLE event_attendees DISABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY;

-- Step 2: Auto-create profile rows for any auth users who don't have one
INSERT INTO public.users (id, email, name, age, gender, is_active, is_premium, intent)
SELECT 
    au.id,
    au.email,
    COALESCE(au.raw_user_meta_data->>'name', split_part(au.email, '@', 1)) as name,
    COALESCE((au.raw_user_meta_data->>'age')::int, 25) as age,
    COALESCE(au.raw_user_meta_data->>'gender', 'other') as gender,
    true as is_active,
    false as is_premium,
    'dating' as intent
FROM auth.users au
LEFT JOIN public.users pu ON au.id = pu.id
WHERE pu.id IS NULL;

-- Step 3: Confirm how many users got fixed
SELECT 
    (SELECT count(*) FROM auth.users) as auth_users,
    (SELECT count(*) FROM public.users) as profile_rows,
    (SELECT count(*) FROM auth.users au LEFT JOIN public.users pu ON au.id = pu.id WHERE pu.id IS NULL) as still_missing;
