# 💘 LinkUp — Full Dating Platform

> **Find your person. For real.**  
> A full-featured dating app built with Streamlit + Supabase, designed for the East African market with M-Pesa payments.

---

## 🚀 Quick Start (5 Steps)

### Step 1 — Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/linkup-dating-app
cd linkup-dating-app
pip install -r requirements.txt
```

### Step 2 — Set Up Supabase
1. Go to your Supabase project: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh
2. Go to **Settings → API**
3. Copy the **`anon` `public`** key (starts with `eyJ...`)
4. Also copy the **Project URL**

### Step 3 — Configure `.env`
```bash
cp .env.example .env
```
Edit `.env` and fill in:
```
SUPABASE_URL=https://knhkbjyorbsjhwxnchlh.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...   ← from step 2
CLOUDINARY_CLOUD_NAME=linkup
CLOUDINARY_API_KEY=358977134356166
CLOUDINARY_API_SECRET=ZD2g4KkmTwJbQ2H798LBhO-LCek
```

### Step 4 — Run the Database Schema
1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/sql/new
2. Open `database/schema.sql`, copy ALL contents
3. Paste into SQL Editor → click **Run**

### Step 5 — Launch
```bash
streamlit run app.py
```
Open http://localhost:8501 — you'll see the setup wizard if anything is missing.

---

## 📁 Project Structure

```
linkup-dating-app/
├── app.py                  # Main entry point + router
├── requirements.txt
├── .env                    # Your secrets (never commit!)
├── .streamlit/
│   └── config.toml         # Theme (LinkUp red)
│
├── components/             # Reusable UI
│   ├── navbar.py
│   ├── profile_card.py
│   └── chat_box.py
│
├── pages/                  # App screens
│   ├── login.py
│   ├── register.py
│   ├── home.py             # Dashboard
│   ├── discover.py         # Swipe / browse
│   ├── matches.py
│   ├── chat.py
│   ├── profile.py
│   ├── settings.py         # Premium + M-Pesa
│   ├── events.py
│   ├── reset_password.py
│   └── admin.py            # Moderation panel
│
├── utils/                  # Backend logic
│   ├── db.py               # All Supabase queries
│   ├── auth.py             # Login / register / session
│   ├── matching.py         # Match scoring algorithm
│   ├── filters.py          # Discovery filters
│   ├── media.py            # Cloudinary uploads
│   ├── payments.py         # M-Pesa Daraja API
│   └── startup_check.py    # Config validator
│
├── assets/
│   └── styles.css          # Global styles
│
└── database/
    └── schema.sql          # Full PostgreSQL schema
```

---

## ⚙️ Features

| Feature | Status |
|---|---|
| Email/Password Auth | ✅ |
| User Profiles + Photos | ✅ |
| Like / Pass / Match | ✅ |
| Real-time Chat | ✅ |
| Discovery Filters | ✅ |
| Match Scoring Algorithm | ✅ |
| Intent Mode (Dating/Friends/Network) | ✅ |
| Events (Meetups) | ✅ |
| Report & Block Users | ✅ |
| Admin Moderation Panel | ✅ |
| M-Pesa Premium Payments | ✅ |
| Cloudinary Photo Upload | ✅ |
| Profile Completion Bar | ✅ |
| Notifications | ✅ |
| Distance Calculation | ✅ |
| Premium Features (Undo, See Likes) | ✅ |

---

## 🔐 Getting Your Supabase Anon Key

The most common setup issue is the missing anon key. Here's exactly where to find it:

1. Visit: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/settings/api
2. Scroll to **"Project API Keys"**
3. Click the eye icon next to **`anon` `public`**
4. Copy the full key → paste into `.env` as `SUPABASE_ANON_KEY`

---

## 💰 M-Pesa Setup

1. Register at https://developer.safaricom.co.ke
2. Create an app → get Consumer Key + Consumer Secret
3. Add to `.env`:
```
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_SHORTCODE=174379       # Safaricom sandbox shortcode
MPESA_PASSKEY=...            # From developer portal
MPESA_CALLBACK_URL=https://your-app.streamlit.app/mpesa/callback
```

---

## ☁️ Deploy to Streamlit Cloud

1. Push to GitHub (make sure `.env` is in `.gitignore`)
2. Go to https://streamlit.io/cloud → New app
3. Connect your GitHub repo → select `app.py`
4. In **Advanced settings → Secrets**, add your `.env` contents in TOML format:
```toml
SUPABASE_URL = "https://knhkbjyorbsjhwxnchlh.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
CLOUDINARY_CLOUD_NAME = "linkup"
CLOUDINARY_API_KEY = "358977134356166"
CLOUDINARY_API_SECRET = "ZD2g4KkmTwJbQ2H798LBhO-LCek"
```
5. Click Deploy!

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
- **Images:** Cloudinary
- **Payments:** M-Pesa Daraja API
- **Hosting:** Streamlit Cloud

---

Built with ❤️ in Nairobi 🇰🇪
