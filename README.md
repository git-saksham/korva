# KORVA

**Performance sportswear. Built for the long run.**

KORVA is a full-stack sportswear storefront for browsing performance and training apparel, choosing product variants, managing a shopping bag, and placing orders. It also includes a separate admin area for managing the catalogue, inventory, customers, and order status.

**Live store:** https://korva-phi.vercel.app/  
**Source code:** https://github.com/git-saksham/korva

---

## What the application includes

### Storefront
- A dark, editorial-style storefront with a responsive layout.
- A home page featuring selected products, bestsellers, new arrivals/recommendations, and sport-led collections.
- A product catalogue with search and filters for category, sport, size, and price.
- Sorting by featured products, newest, price, and name.
- Product detail pages with descriptions, specifications, available sizes, colours, and stock-aware variants.
- Search suggestions backed by a small JSON endpoint.

### Product variants and inventory
Products are modelled separately from their purchasable variants. A variant represents a product's size and colour combination and has its own stock count and SKU. The cart and checkout operate on variant IDs, so availability is checked for the selected option rather than only at product level.

### Accounts, wishlist, and cart
- Account registration, login, logout, and profile editing.
- Passwords stored as hashes through Werkzeug's password-hashing utilities.
- A wishlist for signed-in customers.
- Guest shopping carts that can be merged into a customer's cart after sign-in.
- Quantity updates, item removal, stock validation, and a cart drawer updated through JSON responses.

### Checkout and orders
- Checkout requires a signed-in customer and collects shipping details.
- The server calculates prices, shipping, and totals from database records rather than trusting client-submitted prices.
- Orders preserve a snapshot of the purchased product name, size, colour, and unit price.
- Inventory is reduced when an order is placed and can be restored when an admin cancels an order.
- Shipping is configured as free for orders of ₹5,000 or more; otherwise a flat ₹199 charge applies.

**Payment note:** the repository currently implements a `MockGateway` only. Card and UPI flows are sandbox simulations, and cash on delivery is recorded as pending. It does not currently integrate a live payment processor or move real money.

### Admin area
The protected admin dashboard includes:
- Store overview with product, user, order, and revenue figures.
- Recent order activity and a 14-day revenue chart.
- Product creation, editing, activation, and deletion.
- Variant creation from size/colour combinations.
- Per-variant stock updates and low-stock visibility.
- Order status management.
- Customer listing and order counts.

Admin routes are guarded by login and an admin-role check.

### Product artwork and recommendations
- Product garment artwork is generated as SVG by the application, using garment silhouettes and the selected colour. This provides default catalogue imagery without relying on a third-party image service; an admin-uploaded image can override it.
- Related products and customer recommendations use content-based similarity. The recommender builds TF-IDF features from product names, categories, sport, garment type, and descriptions, then ranks products using cosine similarity. For signed-in users, wishlist and recent purchase history form the recommendation profile.

---

## Technology stack

| Layer | Technologies | How they are used |
|---|---|---|
| Application backend | Python, Flask 3 | Application factory, routes, request handling, sessions, and server-rendered pages |
| Frontend rendering | Jinja2 templates, HTML | Store pages, product details, account pages, checkout, and admin views are rendered on the server |
| Styling and responsive UI | Bootstrap 5.3.3, custom CSS | Bootstrap is loaded from jsDelivr; the KORVA visual system is implemented in `app/static/css/korva.css` |
| Browser interactions | Vanilla JavaScript, Bootstrap bundle | Search suggestions, cart drawer updates, and interactive storefront behaviour in `app/static/js/korva.js` |
| Database layer | Flask-SQLAlchemy, SQLAlchemy 2.x | Relational models, queries, and persistence |
| Database | SQLite by default; PostgreSQL supported through `DATABASE_URL` | Local development defaults to SQLite; a configured database URL can point to PostgreSQL |
| Authentication and forms | Flask-Login, Flask-WTF, WTForms | User sessions, protected routes, form validation, and CSRF protection |
| Schema migrations | Flask-Migrate | Database migration integration |
| Recommendations | pandas, NumPy, scikit-learn | TF-IDF vectorization and cosine-similarity ranking |
| Image handling | Pillow | Validates uploaded product images |
| SVG artwork | Python-generated SVG | Procedural product and hero artwork |
| Hosting adapter | Vercel Python runtime | `api/index.py` exposes the Flask application to Vercel through `vercel.json` |

The exact Python package versions and constraints are listed in [requirements.txt](requirements.txt).

---

## How it is structured

KORVA uses a **server-rendered Flask architecture**, rather than a separate React/Node frontend and backend. Flask routes load data from SQLAlchemy models and render Jinja templates. A small amount of browser-side JavaScript enhances interactions such as the cart drawer and product search.

```text
korva/
├── api/
│   └── index.py                 # Vercel entry point for the Flask app
├── app/
│   ├── __init__.py              # Application factory, extensions, filters, error handlers
│   ├── extensions.py            # SQLAlchemy, Login, CSRF, and migration extensions
│   ├── models.py                # Users, products, variants, carts, orders, payments
│   ├── forms.py                 # Login, registration, checkout, and profile forms
│   ├── auth/
│   │   └── routes.py             # Registration, login, logout, admin access guard
│   ├── admin/
│   │   └── routes.py             # Admin dashboard, catalogue, stock, and order operations
│   ├── routes/
│   │   ├── main.py               # Home, shop, product pages, search, wishlist, SVG routes
│   │   ├── cart.py               # Cart state, add, update, and remove operations
│   │   └── shop_account.py       # Checkout, customer account, and order details
│   ├── services/
│   │   ├── art.py                # Procedural SVG garment and hero artwork
│   │   ├── cart.py               # Cart retrieval, guest-cart merge, and totals
│   │   ├── payments.py           # Payment gateway interface and mock implementation
│   │   └── recommender.py        # TF-IDF and cosine-similarity recommendations
│   ├── templates/                # Jinja storefront, account, checkout, and admin templates
│   └── static/
│       ├── css/korva.css         # Custom storefront styles
│       ├── js/korva.js           # Client-side interactions
│       └── uploads/              # Product image uploads (local configuration)
├── seed/
│   └── seed.py                   # Demo catalogue and optional demo data
├── config.py                    # Environment-based app and database configuration
├── requirements.txt              # Python dependencies
├── vercel.json                  # Vercel Python runtime and routing configuration
└── wsgi.py                      # WSGI entry point
```

---

## Data model

The main relational entities are:

- **User** — customer identity, password hash, and admin flag.
- **Category** — catalogue grouping.
- **Product** — product description, price, sport, garment type, and merchandising flags.
- **ProductVariant** — size/colour combination, SKU, and available stock.
- **Cart / CartItem** — guest or signed-in cart and its selected variants.
- **WishlistItem** — saved products for a customer.
- **Order / OrderItem** — order totals, shipping details, and a snapshot of each purchased line.
- **Payment** — payment provider, method, reference, amount, and status.

This separation allows stock to be tracked at the size-and-colour level while order history retains the details and price that applied when the order was placed.

---

## Run locally

### Requirements
- Python 3.10 or newer
- pip

### Setup

```bash
git clone https://github.com/git-saksham/korva.git
cd korva

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root and set a development secret:

```env
SECRET_KEY=replace-with-a-long-random-secret
```

Initialize the database and load the demo catalogue:

```bash
flask --app wsgi:app init-db
flask --app wsgi:app seed
```

Start the development server:

```bash
flask --app wsgi:app run --debug
```

Open http://127.0.0.1:5000.

The seed command loads the sample product catalogue and, outside production mode, demo customer/order data. The seed script also contains a development admin account; configure `ADMIN_EMAIL` and `ADMIN_PASSWORD` to create an admin with your own credentials, or use the Flask CLI command:

```bash
flask --app wsgi:app create-admin --email you@example.com --password 'use-a-strong-password' --name 'Store Admin'
```

---

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session and security signing key; set a strong value outside local development |
| `DATABASE_URL` | Optional SQLAlchemy database URL; PostgreSQL URLs are normalized |
| `PAYMENT_PROVIDER` | Currently supports `mock` only |
| `AUTO_SEED` | Set to `1` to create tables and seed data during app startup |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Credentials used by the seed/admin creation logic |
| `FLASK_ENV` | Controls production-specific cookie and seed behaviour |

When the Vercel environment is detected and no `DATABASE_URL` is supplied, the configuration points SQLite to `/tmp/korva.db`. This is suitable for a demo-style runtime, not durable production storage. For persistent production data, configure a managed database through `DATABASE_URL`. Uploaded files also use temporary storage on Vercel, so persistent product-image storage would require an external storage service.

---

## Current implementation boundaries

- Payments are mocked; no live Razorpay, Stripe, or other payment gateway is connected.
- The recommendation engine is content-based and uses product metadata plus a customer's wishlist/order history; it is not a trained deep-learning model.
- The project is a Flask/Jinja application with progressive JavaScript interactions, not a React, Next.js, or Node.js application.
- SQLite is the default database configuration. PostgreSQL support is provided through the SQLAlchemy connection URL.
- The Vercel fallback SQLite database and uploaded files use temporary filesystem locations; they should not be treated as durable persistent storage.

---

## Links

- **Live website:** https://korva-phi.vercel.app/
- **GitHub repository:** https://github.com/git-saksham/korva
