# Ashritha Jewellers — Complete Deployment Guide

---

## YOUR FILE STRUCTURE

```
Ashritha Jewellers/
├── index.html                  ← Your complete website
└── backend/
     ├── app.py                 ← Main server file
     ├── requirements.txt       ← Python packages needed
     ├── .env.example           ← Copy this to .env
     ├── config/
     │    └── database.py       ← Database setup
     ├── middleware/
     │    └── auth.py           ← Login security
     └── routes/
          ├── auth.py           ← Register / Login / Profile
          ├── products.py       ← Products CRUD + Stock
          ├── orders.py         ← Orders management
          ├── reviews.py        ← Reviews + moderation
          ├── rent.py           ← Jewellery rent requests
          └── settings.py      ← Store settings
```

---

## PHASE 1 — RUN LOCALLY (YOUR COMPUTER)

### Step 1 — First time setup (do this only once)

Open PowerShell inside your `backend` folder and run:

```
python app.py
```

The database (`ashritha.db`) is created automatically with all sample data.

You should see:
```
╔══════════════════════════════════════════════════════╗
║   Ashritha Jewellers API  v2.0                       ║
║   http://localhost:5000                              ║
║   Admin: admin@ashritha.com / admin123               ║
╚══════════════════════════════════════════════════════╝
```

### Step 2 — Test the backend is working

Open Chrome and visit: `http://localhost:5000/api/health`

You should see: `{"status": "ok"}`

### Step 3 — Open your website

Double-click `index.html` — it opens in Chrome.

**The website currently uses localStorage (local storage).** That is fine for testing. After deployment you will connect it to the real backend.

---

## PHASE 2 — CONNECT WEBSITE TO BACKEND

This step makes the website talk to your real database instead of browser storage.

At the top of the `<script>` section in `index.html`, find this line:

```javascript
const ADMIN_EMAIL='admin@ashritha.com', ADMIN_PASS='admin123';
```

Add this line right below it:

```javascript
const API = 'http://localhost:5000';  // Change to your Render URL after deployment
```

Then any time the website needs to load products, it will call:
```
GET http://localhost:5000/api/products
```

I will build the full connected frontend version for you separately — just ask when you are ready.

---

## PHASE 3 — DEPLOY BACKEND TO RENDER (FREE)

Render is a free hosting service that runs your Python backend online 24/7.

### Step 1 — Create a GitHub account

1. Go to **github.com**
2. Click **Sign Up** — use any email
3. Complete signup

### Step 2 — Upload your backend to GitHub

1. After signing in, click the **+** icon (top right) → **New repository**
2. Name it: `ashritha-backend`
3. Make it **Private**
4. Click **Create repository**
5. On the next page, click **"uploading an existing file"**
6. Upload ALL files from your `backend` folder (including subfolders)
7. Click **Commit changes**

### Step 3 — Create Render account

1. Go to **render.com**
2. Click **Get Started for Free**
3. Sign up with the same Gmail you used for GitHub
4. Click **Connect GitHub** and allow access

### Step 4 — Deploy on Render

1. Click **New +** → **Web Service**
2. Select your `ashritha-backend` repository
3. Fill in these settings:

| Setting | Value |
|---|---|
| Name | `ashritha-jewellery-api` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Instance Type | `Free` |

5. Scroll down to **Environment Variables** — click **Add Environment Variable**:

| Key | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | (type any long random text, e.g. `Ashritha2025@SecretKey!Gold`) |
| `JWT_SECRET` | (type any long random text, e.g. `AJ_JWT_2025_Secure_Key!`) |
| `FRONTEND_URL` | (leave blank for now — fill after Netlify step) |

6. Click **Create Web Service**
7. Wait 3–5 minutes for it to deploy
8. You get a URL like: `https://ashritha-jewellery-api.onrender.com`
9. Test it: open `https://ashritha-jewellery-api.onrender.com/api/health` in Chrome

You should see: `{"status": "ok"}` ✅

**Save this URL — you will need it in the next step.**

---

## PHASE 4 — DEPLOY WEBSITE TO NETLIFY (FREE)

### Step 1 — Create Netlify account

1. Go to **netlify.com**
2. Click **Sign Up** → **Sign up with GitHub**

### Step 2 — Deploy your website

1. After signing in, you see the dashboard
2. Look for the box that says **"Drag and drop your site folder here"**
3. Find your `index.html` file on your Desktop
4. Drag **only the `index.html` file** into that box
5. Wait 30 seconds
6. Netlify gives you a link like: `random-name-123.netlify.app`

### Step 3 — Set a custom site name

1. Click **Site settings** → **Change site name**
2. Type: `ashritha-jewellery`
3. Your website is now at: `https://ashritha-jewellery.netlify.app` ✅

### Step 4 — Update your backend CORS settings

Now that your website has a real URL, go to Render:
1. Open your web service on Render
2. Click **Environment** tab
3. Find `FRONTEND_URL`
4. Set value to: `https://ashritha-jewellery.netlify.app`
5. Click **Save** — Render redeploys automatically (1–2 min)

---

## PHASE 5 — CONNECT WEBSITE TO LIVE BACKEND

Now update `index.html` to use your real backend URL instead of localhost.

In `index.html`, find the line:
```javascript
const API = 'http://localhost:5000';
```

Change it to:
```javascript
const API = 'https://ashritha-jewellery-api.onrender.com';
```

Then re-upload `index.html` to Netlify:
1. Go to your site on Netlify
2. Click **Deploys** tab
3. Drag and drop your updated `index.html` into the deploy box
4. Done — live in 30 seconds ✅

---

## PHASE 6 — CUSTOM DOMAIN (OPTIONAL)

If you want `ashrithajewellery.com` instead of `.netlify.app`:

### Buy a domain

Recommended providers (cheapest):
- **GoDaddy** (godaddy.com) — around Rs 800–1200/year
- **Namecheap** (namecheap.com) — around $10/year

Search for `ashrithajewellery.com` and buy it.

### Connect to Netlify

1. In Netlify → **Site settings** → **Domain management**
2. Click **Add custom domain**
3. Type your domain: `ashrithajewellery.com`
4. Netlify shows you DNS settings to copy
5. Go to your domain provider → DNS settings
6. Add the records Netlify gives you
7. Wait 24 hours for DNS to propagate
8. Netlify automatically adds **free HTTPS/SSL** ✅

---

## PHASE 7 — CHANGE ADMIN PASSWORD (IMPORTANT!)

**Do this immediately after deployment.**

Using any API tool like Postman or this URL format:

```
POST https://ashritha-jewellery-api.onrender.com/api/auth/login
Body: {"email": "admin@ashritha.com", "password": "admin123"}
```

Copy the `token` from the response, then:

```
PUT https://ashritha-jewellery-api.onrender.com/api/auth/profile
Header: Authorization: Bearer <your_token>
Body: {"fname": "Admin", "new_password": "YourNewStrongPassword!"}
```

---

## DAILY BACKUP

Your database is stored in `ashritha.db` inside your backend folder on Render. To back it up:

1. Go to Render dashboard → your web service
2. Click **Shell** tab
3. Type: `cp ashritha.db ashritha_backup_$(date +%Y%m%d).db`

Alternatively, download it via the Render Files section.

---

## COMPLETE API REFERENCE

### Base URL
- **Local:** `http://localhost:5000`
- **Production:** `https://ashritha-jewellery-api.onrender.com`

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | — | Create account |
| POST | `/api/auth/login` | — | Login, returns token |
| GET | `/api/auth/me` | User | Get my profile |
| PUT | `/api/auth/profile` | User | Update profile / password |

### Products (Public)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | All active products |
| GET | `/api/products?category=necklace` | Filter by category |
| GET | `/api/products?rent=1` | Rentable only |
| GET | `/api/products?q=kundan` | Search |
| GET | `/api/products?sort=price-asc` | Sorted |
| GET | `/api/products/:id` | Single product |
| GET | `/api/products/:id/reviews` | Product reviews |

### Products (Admin)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/products` | All products |
| POST | `/api/admin/products` | Add product |
| PUT | `/api/admin/products/:id` | Edit product |
| PUT | `/api/admin/products/:id/stock` | Update stock |
| PUT | `/api/admin/products/:id/toggle` | Show / hide |
| DELETE | `/api/admin/products/:id` | Delete |

### Orders
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/orders` | Optional | Place order |
| GET | `/api/orders/my` | User | My orders |
| GET | `/api/admin/orders` | Admin | All orders |
| PUT | `/api/admin/orders/:id/status` | Admin | Update status |

### Reviews
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/products/:id/reviews` | Optional | Submit review |
| GET | `/api/admin/reviews?status=pending` | Admin | Pending reviews |
| PUT | `/api/admin/reviews/:id/approve` | Admin | Approve review |
| DELETE | `/api/admin/reviews/:id` | Admin | Delete review |

### Rent
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/rent` | Optional | Submit rent request |
| GET | `/api/rent/my` | User | My rent requests |
| GET | `/api/admin/rent` | Admin | All rent requests |
| PUT | `/api/admin/rent/:id/status` | Admin | Update rent status |

### Settings
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/settings/public` | — | Store settings |
| PUT | `/api/admin/settings` | Admin | Update settings |

---

## TROUBLESHOOTING

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'config'` | Run `python app.py` from inside the `backend` folder, not from outside |
| `python is not recognized` | Reinstall Python, tick "Add to PATH" during install |
| Render deployment fails | Check the Build Logs tab on Render for the exact error |
| Website shows old data after update | Hard refresh: press `Ctrl + Shift + R` in Chrome |
| WhatsApp button not working | Go to Admin → Settings and set your real WhatsApp number |
| CORS error in browser console | Make sure `FRONTEND_URL` in Render environment matches your Netlify URL exactly |

---

## SUMMARY CHECKLIST

- [ ] Backend runs locally (`python app.py`)
- [ ] Website opens locally (`index.html`)
- [ ] Changed WhatsApp number in Admin → Settings
- [ ] Pushed backend to GitHub
- [ ] Deployed backend to Render
- [ ] Deployed website to Netlify
- [ ] Updated `FRONTEND_URL` in Render
- [ ] Updated `API` URL in `index.html` to Render URL
- [ ] Re-uploaded updated `index.html` to Netlify
- [ ] Changed admin password
- [ ] Added real products in Admin panel
- [ ] Tested full order flow on live site
