# Saree Store — Django ecommerce (SQLite)

## Quick start (localhost)

```powershell
cd saree_store
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

- **Storefront:** http://127.0.0.1:8000/
- **Custom admin:** http://127.0.0.1:8000/store-admin/login/  
  Default superuser from `seed_demo`: **admin** / **admin123** (change immediately).

Django’s built-in `/admin/` URL is **not** registered; store operations use the custom dashboard only.

## Environment variables (optional)

Copy `.env.example` to `.env` and adjust values for your host (or export variables in your shell / hosting panel).

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Production secret |
| `DJANGO_DEBUG` | `false` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay checkout |
| `WHATSAPP_PROVIDER` | `auto` (default), `meta`, `twilio`, or `stub` (console only) |
| `META_WHATSAPP_TOKEN`, `META_WHATSAPP_PHONE_NUMBER_ID`, `META_WHATSAPP_API_VERSION` | [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp (e.g. `whatsapp:+14155238886`) |

With **`WHATSAPP_PROVIDER=auto`**, Meta is used when token + phone number ID are set; otherwise Twilio if configured; otherwise messages are logged to the console. Indian numbers are normalized to `+91…` / digits for Meta.

Without Razorpay keys, checkout still works with **COD**.

## Project layout

- `apps/` — `accounts`, `products`, `cart`, `orders`, `payments`, `adminpanel`, `reviews`, `wishlist`
- `templates/` — storefront + admin templates
- `static/` — JS (live search, etc.)
- `media/` — uploaded product/banner/review images
- `services/` — Razorpay + WhatsApp (Meta Cloud API and/or Twilio)

## Production notes

Use a real WSGI server (e.g. Gunicorn + Nginx), set `DEBUG=False`, configure `ALLOWED_HOSTS`, serve `MEDIA`/`STATIC` via the web server, and use environment-based secrets.
