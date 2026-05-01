# Ashritha Jewellers — Backend API

## Stack
- **Python 3.12** + **Flask 3**
- **SQLite** (file: `ashritha.db` in project root)
- **PyJWT** for authentication
- **Werkzeug** for password hashing

---

## Quick Start

```bash
cd backend
python app.py
# API runs on http://localhost:5000
```

---

## Database
SQLite database auto-creates at first run with:
- Admin user: `admin@ashritha.com` / `admin123`
- 10 sample products
- Default store settings

---

## Authentication
All protected endpoints require a `Bearer` token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```
Tokens are returned from `/api/auth/login` and `/api/auth/register`.

---

## API Endpoints

### Health
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | None | Server health check |

---

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | None | Create new customer account |
| POST | `/api/auth/login` | None | Login, returns JWT token |
| GET  | `/api/auth/me` | User | Get current user profile |
| PUT  | `/api/auth/profile` | User | Update profile / password |
| POST | `/api/auth/logout` | None | Logout (client clears token) |

**Register body:**
```json
{
  "fname": "Priya",
  "lname": "Reddy",
  "email": "priya@gmail.com",
  "phone": "+91 9876543210",
  "password": "mypassword123"
}
```

**Login body:**
```json
{ "email": "priya@gmail.com", "password": "mypassword123" }
```

**Login response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": 2,
    "fname": "Priya",
    "email": "priya@gmail.com",
    "is_admin": false
  }
}
```

---

### Products (Public)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/products` | None | List all active products |
| GET | `/api/products?category=silver` | None | Filter by category |
| GET | `/api/products?sort=price-asc` | None | Sort (default/price-asc/price-desc/newest) |
| GET | `/api/products?q=kundan` | None | Search by name/description |
| GET | `/api/products/:id` | None | Single product detail |

**Categories:** `necklace`, `earrings`, `bangles`, `sets`, `rings`, `silver`

---

### Products (Admin)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET    | `/api/admin/products` | Admin | All products (incl. hidden) |
| POST   | `/api/admin/products` | Admin | Add new product |
| PUT    | `/api/admin/products/:id` | Admin | Edit product |
| PUT    | `/api/admin/products/:id/stock` | Admin | Update stock count only |
| PUT    | `/api/admin/products/:id/toggle` | Admin | Toggle visible/hidden |
| DELETE | `/api/admin/products/:id` | Admin | Delete product |

**Add Product body:**
```json
{
  "name": "Kundan Necklace Set",
  "category": "necklace",
  "price": 1850,
  "mrp": 2800,
  "stock": 10,
  "badge": "Bestseller",
  "description": "Beautiful kundan work...",
  "image_url": "https://..."
}
```

**Update Stock body:**
```json
{ "stock": 15 }
```

---

### Orders
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/orders` | Optional | Place an order (guest or logged in) |
| GET  | `/api/orders/my` | User | My order history |
| GET  | `/api/admin/orders` | Admin | All orders |
| GET  | `/api/admin/orders?status=pending` | Admin | Filter by status |
| GET  | `/api/admin/orders/:id` | Admin | Order detail with items |
| PUT  | `/api/admin/orders/:id/status` | Admin | Update order status |

**Place Order body:**
```json
{
  "customer_name": "Priya Reddy",
  "customer_phone": "+91 9876543210",
  "address": "12, Rose Street, Banjara Hills",
  "city": "Hyderabad",
  "state": "Telangana",
  "pin_code": "500034",
  "notes": "Gift wrap please",
  "items": [
    { "product_id": 1, "qty": 1 },
    { "product_id": 3, "qty": 2 }
  ]
}
```

**Order Statuses:** `pending`, `confirmed`, `shipped`, `delivered`, `cancelled`

---

### Settings
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/settings/public` | None | Public store settings |
| GET | `/api/admin/settings` | Admin | All settings |
| PUT | `/api/admin/settings` | Admin | Update settings |

**Update Settings body (any subset):**
```json
{
  "wa_number": "919876543210",
  "upi_id": "ashritha@upi",
  "ann_text": "Sale On Now!",
  "free_shipping": "499",
  "shipping_charge": "50",
  "store_name": "Ashritha Jewellers"
}
```

---

## Stock Auto-Management
When an order is placed:
1. Each product's stock is reduced by the ordered quantity
2. If stock reaches 0, the product automatically shows "Out of Stock" to customers
3. The frontend reads `stock_status` field: `"in"` / `"low"` (1–3 left) / `"oos"` (0)

---

## Error Format
All errors return consistent JSON:
```json
{ "error": "Human-readable message" }
```

HTTP codes used: `200`, `201`, `400`, `401`, `403`, `404`, `409`, `500`

---

## Frontend Integration
The frontend (`index.html`) currently uses `localStorage`.  
To connect it to this API, update the `API_BASE` constant in the JS section and replace localStorage calls with `fetch()` calls to these endpoints.

---

## Production Checklist
- [ ] Change `SECRET_KEY` and `JWT_SECRET` in `.env`
- [ ] Change admin password via API after first login
- [ ] Set `FLASK_ENV=production`
- [ ] Use a proper WSGI server (gunicorn): `gunicorn app:app`
- [ ] Add your domain to `ALLOWED_ORIGINS` in `app.py`
- [ ] Set up HTTPS (SSL certificate)
- [ ] Back up `ashritha.db` regularly
