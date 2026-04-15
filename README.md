# 💘 LinkUp — Full Dating Platform

> **Find your person. For real.**
> A full-featured dating app built with Streamlit + Supabase, designed for the East African market with M-Pesa payments.

---

## 🚀 Live Demo
Deploy URL: _coming soon_

---

## ✨ Features

### 👤 Authentication
- Email/password registration & login
- Password reset via email
- Session management with Supabase Auth

### 🧑 Profiles
- Photo upload (Cloudinary)
- Name, age, gender, bio, location
- Interest tags (30+ options)
- Profile completion progress bar
- Intent mode: Dating ❤️ / Friendship 🤝 / Networking 💼

### 🔥 Discovery
- Swipe-style profile browsing
- Smart match scoring (interests + proximity + activity)
- Filters: age, gender, distance, intent
- Boosted profiles priority

### 💞 Matching
- Auto-match when both users like each other
- Database trigger creates match instantly
- Unmatch anytime

### 💬 Chat
- Real-time messaging (Supabase Realtime)
- Image sharing
- Read receipts
- Auto-refresh toggle

### 🎯 Intent Modes
- Dating, Friendship, Networking
- Filter discovery by intent

### 🛡️ Safety
- Report users
- Block users
- Hide profile
- Admin moderation panel
- Row Level Security (Supabase RLS)

### 💎 Premium (M-Pesa)
- See who liked you
- Undo swipes
- Unlimited likes
- Profile boost
- M-Pesa STK Push integration

### 🎉 Events
- Create local meetups
- Join events
- Attendee list

### 🔔 Notifications
- Match notifications
- Message alerts
- Like notifications (premium)

---

## 🗂️ Project Structure

```
linkup-dating-app/
├── app.py                    # Entry point & router
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   ├── config.toml           # Theme & server config
│   └── secrets.toml.example
│
├── components/
│   ├── navbar.py             # Navigation bar
│   ├── profile_card.py       # Reusable profile card
│   └── chat_box.py           # Chat UI component
│
├── pages/
│   ├── login.py
│   ├── register.py
│   ├── reset_password.py
│   ├── home.py               # Dashboard
│   ├── discover.py           # Swipe/discover
│   ├── matches.py            # Matches list
│   ├── chat.py               # Messaging
│   ├── profile.py            # Edit profile
│   ├── settings.py           # Premium, safety, account
│   ├── events.py             # Events feature
│   └── admin.py              # Admin panel
│
├── utils/
│   ├── db.py                 # All Supabase queries
│   ├── auth.py               # Auth helpers
│   ├── matching.py           # Match scoring algorithm
│   ├── filters.py            # Discovery filters
│   ├── media.py              # Cloudinary uploads
│   └── payments.py           # M-Pesa Daraja API
│
├── assets/
│   └── styles.css            # Global CSS
│
└── database/
    └── schema.sql            # Full PostgreSQL schema
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/linkup-dating-app.git
cd linkup-dating-app
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 5. Set up Supabase
1. Go to [supabase.com](https://supabase.com) → New Project
2. Copy your Project URL and anon key to `.env`
3. Open **SQL Editor** in Supabase dashboard
4. Run the contents of `database/schema.sql`
5. Enable **Realtime** for `messages` and `notifications` tables

### 6. Set up Cloudinary
1. Go to [cloudinary.com](https://cloudinary.com) → Free account
2. Copy Cloud Name, API Key, API Secret to `.env`

### 7. Run the app
```bash
streamlit run app.py
```

---

## 🚀 Deployment (Streamlit Cloud)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py`
4. Add secrets in **Settings → Secrets** (copy from `.streamlit/secrets.toml.example`)
5. Deploy!

---

## 💰 Monetization (M-Pesa)

| Plan | Price | Duration | Features |
|------|-------|----------|----------|
| Free | KES 0 | Forever | 10 likes/day, basic features |
| Boost | KES 100 | 7 days | Profile priority, 3x visibility |
| Premium | KES 500 | 30 days | All features + see who liked you |

---

## 🗄️ Database Schema

Key tables:
- `users` — profiles, preferences, premium status
- `likes` — who liked who
- `passes` — who was skipped
- `matches` — mutual likes (auto-created by trigger)
- `messages` — chat messages
- `notifications` — in-app notifications
- `reports` / `blocks` — safety
- `events` / `event_attendees` — meetups
- `subscriptions` — payment history

---

## 🧠 Match Scoring Algorithm

```
Score = (Shared Interests × 40%)
      + (Proximity Score × 30%)
      + (Activity Recency × 20%)
      + (Profile Completeness × 10%)
```

---

## 🛣️ Roadmap

- [ ] **v1.0** — Auth + Profile + Like/Match + Chat ✅
- [ ] **v1.1** — Events + Admin panel ✅
- [ ] **v1.2** — Push notifications (Firebase)
- [ ] **v1.3** — Video calls (Agora / Daily.co)
- [ ] **v2.0** — React Native mobile app
- [ ] **v2.1** — AI smart matching + profile tips

---

## 🤝 Contributing

Pull requests welcome! For major changes, open an issue first.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👨‍💻 Built With ❤️ in Nairobi

Made for the East African dating market. Integrates with M-Pesa for local payments.

> **Stack:** Python · Streamlit · Supabase · PostgreSQL · Cloudinary · M-Pesa Daraja API
