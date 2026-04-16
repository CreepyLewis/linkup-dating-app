-- ============================================
-- LinkUp Dating App - PostgreSQL / Supabase Schema
-- ============================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis"; -- for location/distance

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,               -- null for OAuth users
    name TEXT NOT NULL,
    age INTEGER CHECK (age >= 18 AND age <= 100),
    gender TEXT CHECK (gender IN ('male', 'female', 'non-binary', 'other')),
    bio TEXT,
    location TEXT,                    -- city name
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    interests TEXT[] DEFAULT '{}',    -- array of interest tags
    photo_url TEXT,                   -- primary photo
    photos TEXT[] DEFAULT '{}',       -- all photos
    intent TEXT DEFAULT 'dating' CHECK (intent IN ('dating', 'friendship', 'networking')),
    gender_preference TEXT DEFAULT 'any',
    age_min INTEGER DEFAULT 18,
    age_max INTEGER DEFAULT 60,
    max_distance INTEGER DEFAULT 50,  -- km
    is_premium BOOLEAN DEFAULT FALSE,
    is_boosted BOOLEAN DEFAULT FALSE,
    boost_expires_at TIMESTAMPTZ,
    profile_hidden BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- LIKES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    liked_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, liked_user_id)
);

-- ============================================
-- PASSES (DISLIKES) TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS passes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    passed_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, passed_user_id)
);

-- ============================================
-- MATCHES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user1_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    matched_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user1_id, user2_id)
);

-- ============================================
-- MESSAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    media_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- REPORTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    details TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- BLOCKS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(blocker_id, blocked_user_id)
);

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('match', 'message', 'like', 'boost', 'event')),
    title TEXT NOT NULL,
    body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- EVENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    event_date TIMESTAMPTZ NOT NULL,
    max_attendees INTEGER DEFAULT 50,
    cover_image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- EVENT ATTENDEES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS event_attendees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, user_id)
);

-- ============================================
-- PREMIUM SUBSCRIPTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan TEXT NOT NULL CHECK (plan IN ('boost', 'premium')),
    amount INTEGER NOT NULL,          -- in KES
    mpesa_receipt TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled')),
    starts_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_users_location ON users(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_users_intent ON users(intent);
CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id);
CREATE INDEX IF NOT EXISTS idx_likes_liked ON likes(liked_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_user1 ON matches(user1_id);
CREATE INDEX IF NOT EXISTS idx_matches_user2 ON matches(user2_id);
CREATE INDEX IF NOT EXISTS idx_messages_match ON messages(match_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

-- ============================================
-- ROW LEVEL SECURITY (Supabase RLS)
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- ── users ────────────────────────────────────────────────────────────────────
-- Any authenticated user can insert their own profile row (required for registration)
CREATE POLICY "Users insert own profile" ON users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Users can read non-hidden, active profiles
CREATE POLICY "Public profiles visible" ON users
    FOR SELECT USING (profile_hidden = FALSE AND is_active = TRUE);

-- Users can update their own profile
CREATE POLICY "Users update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

-- ── likes ────────────────────────────────────────────────────────────────────
-- Users manage their own likes
CREATE POLICY "Users manage own likes" ON likes
    FOR ALL USING (auth.uid() = user_id);

-- ── passes ───────────────────────────────────────────────────────────────────
ALTER TABLE passes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own passes" ON passes
    FOR ALL USING (auth.uid() = user_id);

-- ── blocks ───────────────────────────────────────────────────────────────────
ALTER TABLE blocks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own blocks" ON blocks
    FOR ALL USING (auth.uid() = blocker_id);

-- ── matches ──────────────────────────────────────────────────────────────────
-- Users see their own matches
CREATE POLICY "Users see own matches" ON matches
    FOR SELECT USING (auth.uid() = user1_id OR auth.uid() = user2_id);

-- Matches are inserted by the trigger (runs as SECURITY DEFINER), not by the client
-- But allow insert so the Python fallback create_match() also works
CREATE POLICY "Users insert own matches" ON matches
    FOR INSERT WITH CHECK (auth.uid() = user1_id OR auth.uid() = user2_id);

-- ── messages ─────────────────────────────────────────────────────────────────
-- Users see messages in their matches
CREATE POLICY "Users see own messages" ON messages
    FOR SELECT USING (auth.uid() = sender_id OR auth.uid() = receiver_id);

-- Users insert their own messages
CREATE POLICY "Users send messages" ON messages
    FOR INSERT WITH CHECK (auth.uid() = sender_id);

-- Users mark messages as read
CREATE POLICY "Users update own messages" ON messages
    FOR UPDATE USING (auth.uid() = receiver_id);

-- ── notifications ─────────────────────────────────────────────────────────────
CREATE POLICY "Users see own notifications" ON notifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users update own notifications" ON notifications
    FOR UPDATE USING (auth.uid() = user_id);

-- ============================================
-- HELPER FUNCTION: Calculate distance (km)
-- ============================================
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    R DOUBLE PRECISION := 6371; -- Earth radius km
    dLat DOUBLE PRECISION;
    dLon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
BEGIN
    dLat := radians(lat2 - lat1);
    dLon := radians(lon2 - lon1);
    a := sin(dLat/2)^2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)^2;
    c := 2 * atan2(sqrt(a), sqrt(1-a));
    RETURN R * c;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGER: Auto-create match when mutual like
-- ============================================
CREATE OR REPLACE FUNCTION check_mutual_like()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if liked_user already liked this user
    IF EXISTS (
        SELECT 1 FROM likes
        WHERE user_id = NEW.liked_user_id
        AND liked_user_id = NEW.user_id
    ) THEN
        -- Create match (ensure consistent ordering)
        INSERT INTO matches (user1_id, user2_id)
        VALUES (
            LEAST(NEW.user_id, NEW.liked_user_id),
            GREATEST(NEW.user_id, NEW.liked_user_id)
        )
        ON CONFLICT DO NOTHING;

        -- Notify both users
        INSERT INTO notifications (user_id, type, title, body, related_user_id)
        VALUES
            (NEW.user_id, 'match', '🎉 New Match!', 'You have a new match!', NEW.liked_user_id),
            (NEW.liked_user_id, 'match', '🎉 New Match!', 'You have a new match!', NEW.user_id);
    ELSE
        -- Notify liked user of the like (premium feature reveal)
        INSERT INTO notifications (user_id, type, title, body, related_user_id)
        VALUES (NEW.liked_user_id, 'like', '❤️ Someone liked you!', 'Someone liked your profile!', NEW.user_id);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_like_created
    AFTER INSERT ON likes
    FOR EACH ROW EXECUTE FUNCTION check_mutual_like();

-- ============================================
-- TRIGGER: Notify on new message
-- ============================================
CREATE OR REPLACE FUNCTION notify_new_message()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notifications (user_id, type, title, body, related_user_id)
    VALUES (NEW.receiver_id, 'message', '💬 New Message', 'You have a new message!', NEW.sender_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_message_created
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION notify_new_message();
