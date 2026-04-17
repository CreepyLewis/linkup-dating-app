# How to Run LinkUp

## Local (your computer)

### Step 1 - The .env file
The `.env` file is **already inside the project folder** - you do NOT need to create or edit it.
It is at: `linkup-dating-app/.env`  
All your Supabase and M-Pesa keys are already filled in.

### Step 2 - Install packages
Open a terminal, go into the project folder, run:
```
pip install -r requirements.txt
```

### Step 3 - Set up database (do this ONCE)
1. Open: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/sql/new
2. Open file `database/schema.sql` in a text editor
3. Select all (Ctrl+A), copy, paste into Supabase SQL Editor
4. Click **Run**

### Step 4 - Set up photo storage (do this ONCE)
1. Open: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/storage/buckets
2. Click **New bucket** → Name: `avatars` → Tick **Public bucket** → Save
3. Click **New bucket** again → Name: `chat-images` → Tick **Public bucket** → Save

### Step 5 - Run the app
```
streamlit run app.py
```
Opens at http://localhost:8501

---

## Streamlit Cloud (online deployment)

### Step 1 - Push to GitHub
```
git init
git add .
git commit -m "LinkUp v1"
git remote add origin https://github.com/YOUR_USERNAME/linkup-dating-app.git
git push -u origin main
```
**Important:** The `.env` file is excluded from git (it's in .gitignore) - that is correct and safe.

### Step 2 - Deploy
1. Go to https://streamlit.io/cloud
2. Click **New app** → connect your GitHub repo → select `app.py`
3. Click **Advanced settings** → click **Secrets**
4. Copy the contents of `.streamlit/secrets.toml` and paste it in the Secrets box
5. Click **Save** → click **Deploy**

---

## Files you should NEVER edit
- `.env` - already has all your keys, don't touch it
- `database/schema.sql` - already correct
- Any file in `utils/` or `components/` unless told to

## Files safe to customise
- `assets/styles.css` - change colours
- `pages/login.py` - change the welcome text
- `pages/home.py` - change the dashboard layout
