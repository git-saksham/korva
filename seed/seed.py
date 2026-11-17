"""Demo catalogue + optional admin/demo data. Idempotent: skips if products exist."""
import os
import random
from datetime import timedelta

from app.extensions import db
from app.models import Category, Order, OrderItem, Payment, Product, ProductVariant, User, utcnow

COLORS = {
    "Onyx": "#17171a", "Graphite": "#3b3f45", "Bone": "#e6e1d6", "Slate": "#45586b",
    "Moss": "#4a5a44", "Clay": "#a37f6a", "Fog": "#9aa0a6", "Navy": "#1f2a44", "Rust": "#8c4a2f",
}
CATEGORIES = ["Tops", "Bottoms", "Outerwear", "Compression", "Sports Bras"]
STD = ["S", "M", "L", "XL"]
WIDE = ["XS", "S", "M", "L", "XL"]

# name, category, sport, garment, price, compare_at, colours, sizes, flags(F=featured,B=bestseller,N=new), description, specs
P = [
    ("Stride Performance Tee", "Tops", "Running", "tee", 1999, None, ["Onyx", "Bone", "Slate"], STD, "FBN",
     "An ultra-light running tee in a breathable engineered mesh. Zero-distraction seams and a soft drop hem keep you moving mile after mile.",
     "Fabric: 88% recycled polyester, 12% elastane\nFit: Athletic\nWeight: 112 gsm\nFeatures: Laser-cut ventilation, reflective logo\nCare: Machine wash cold"),
    ("Pulse Training Tank", "Tops", "Training", "tank", 1799, None, ["Onyx", "Graphite", "Fog"], STD, "B",
     "A cut-away training tank built for heavy sessions. Four-way stretch fabric moves with every rep and dries in minutes.",
     "Fabric: 82% nylon, 18% elastane\nFit: Relaxed athletic\nWeight: 140 gsm\nFeatures: Dropped armhole, anti-odour finish\nCare: Machine wash cold"),
    ("Apex Seamless Gym Top", "Tops", "Training", "tee", 2299, 2799, ["Graphite", "Clay", "Onyx"], STD, "F",
     "Seamless knit construction with targeted ventilation zones. Quiet, structured and made to hold its shape through the toughest sets.",
     "Fabric: 76% nylon, 24% elastane\nFit: Fitted\nWeight: 160 gsm\nFeatures: Seamless knit, flatlock finish\nCare: Machine wash cold, line dry"),
    ("Flux Long Sleeve Run", "Tops", "Running", "compression", 2599, None, ["Onyx", "Navy"], STD, "N",
     "Thermal-regulating long sleeve for early starts and cold finishes. Thumb loops, zip pocket and 360° reflective detailing.",
     "Fabric: 90% polyester, 10% elastane\nFit: Athletic\nWeight: 190 gsm brushed\nFeatures: Thumb loops, hidden zip pocket\nCare: Machine wash cold"),
    ("Velocity Run Short 5\"", "Bottoms", "Running", "shorts", 2199, None, ["Onyx", "Slate", "Moss"], STD, "FB",
     "Featherweight 5-inch running short with a built-in liner and a secure back pocket. Nothing bounces, nothing rides up.",
     "Fabric: 100% recycled polyester\nInseam: 5 in / 12.5 cm\nWeight: 85 gsm\nFeatures: Brief liner, zip back pocket\nCare: Machine wash cold"),
    ("Torque Training Short 7\"", "Bottoms", "Training", "shorts", 2399, None, ["Graphite", "Onyx", "Bone"], STD, "B",
     "A longer, structured training short with a stretch-woven shell that handles squats, sprints and everything between.",
     "Fabric: 92% nylon, 8% elastane\nInseam: 7 in / 18 cm\nWeight: 150 gsm\nFeatures: Zip pockets, drawcord waist\nCare: Machine wash cold"),
    ("Drift Track Pant", "Bottoms", "Lifestyle", "pants", 3499, None, ["Onyx", "Navy", "Bone"], STD, "F",
     "A tapered track pant with a clean contrast stripe. Warm-up, travel or street — it carries the same quiet confidence.",
     "Fabric: 94% recycled polyester, 6% elastane\nFit: Tapered\nWeight: 210 gsm\nFeatures: Ankle zips, zip pockets\nCare: Machine wash cold"),
    ("Core Training Jogger", "Bottoms", "Training", "pants", 2999, 3599, ["Graphite", "Onyx"], STD, "",
     "Brushed-back jogger with a tapered leg and stretch waistband. Built for recovery days and gym commutes.",
     "Fabric: 80% cotton, 20% polyester\nFit: Tapered\nWeight: 280 gsm\nFeatures: Zip pockets, elastic cuffs\nCare: Machine wash cold"),
    ("Atlas Training Jacket", "Outerwear", "Training", "jacket", 5499, None, ["Onyx", "Slate", "Moss"], STD, "FBN",
     "Our flagship warm-up jacket. Water-repellent stretch shell, full-length YKK zip and articulated sleeves for unrestricted movement.",
     "Fabric: Stretch-woven nylon with DWR finish\nFit: Regular\nWeight: 230 gsm\nFeatures: Zip pockets, reflective trim\nCare: Machine wash cold"),
    ("Gale Wind Shell", "Outerwear", "Running", "jacket", 4999, None, ["Fog", "Onyx"], STD, "N",
     "A packable, wind-blocking shell that disappears into its own pocket. Weighs less than a banana.",
     "Fabric: 100% ripstop nylon\nFit: Regular\nWeight: 62 gsm\nFeatures: Packs into pocket, reflective piping\nCare: Wash cold, no softener"),
    ("Haven Heavyweight Hoodie", "Outerwear", "Lifestyle", "hoodie", 4299, None, ["Onyx", "Clay", "Bone"], STD, "B",
     "A structured heavyweight hoodie in a dense loopback cotton. Oversized hood, clean lines and an embroidered chest mark.",
     "Fabric: 100% organic cotton\nFit: Boxy\nWeight: 420 gsm\nFeatures: Double-layer hood, kangaroo pocket\nCare: Machine wash cold"),
    ("Orbit Quarter-Zip", "Outerwear", "Running", "hoodie", 3799, 4299, ["Navy", "Graphite"], STD, "",
     "A midlayer quarter-zip with a smooth technical face and soft grid interior. Layers under a shell or stands alone.",
     "Fabric: 88% polyester, 12% elastane\nFit: Athletic\nWeight: 220 gsm\nFeatures: Grid fleece, zip chest pocket\nCare: Machine wash cold"),
    ("Grip Compression Tee", "Compression", "Training", "compression", 2799, None, ["Onyx", "Graphite"], STD, "B",
     "Graduated compression for muscle support. A second-skin fit that locks in under any layer.",
     "Fabric: 78% nylon, 22% elastane\nFit: Compression\nWeight: 175 gsm\nFeatures: Graduated compression, flatlock seams\nCare: Machine wash cold"),
    ("Surge Compression Tight", "Compression", "Training", "pants", 3299, None, ["Onyx", "Navy"], STD, "F",
     "Full-length compression tights with a wide waistband and phone pocket. Supportive from first warm-up to last cooldown.",
     "Fabric: 75% nylon, 25% elastane\nFit: Compression\nWeight: 230 gsm\nFeatures: Side pocket, reflective logo\nCare: Machine wash cold"),
    ("Edge Cycling Jersey", "Tops", "Cycling", "tee", 3199, None, ["Onyx", "Rust", "Fog"], STD, "N",
     "A race-cut cycling jersey with a full-length zip, three rear pockets and silicone grippers that keep everything in place.",
     "Fabric: 90% recycled polyester, 10% elastane\nFit: Race\nWeight: 120 gsm\nFeatures: 3 rear pockets, silicone hem grip\nCare: Machine wash cold"),
    ("Slate Court Tank", "Tops", "Basketball", "tank", 1999, None, ["Navy", "Bone", "Onyx"], STD, "",
     "A lightweight court tank with a deep armhole and a soft, quick-drying mesh for fast transitions on the hardwood.",
     "Fabric: 100% polyester mesh\nFit: Relaxed\nWeight: 125 gsm\nFeatures: Deep armhole, cooling mesh\nCare: Machine wash cold"),
    ("Aura Sculpt Sports Bra", "Sports Bras", "Yoga", "bra", 2199, None, ["Onyx", "Clay", "Moss"], WIDE, "FB",
     "Medium-support sports bra with a buttery-soft feel. A scooped neckline and wide underband for all-day comfort.",
     "Fabric: 72% nylon, 28% elastane\nSupport: Medium\nWeight: 190 gsm\nFeatures: Removable pads, wide underband\nCare: Machine wash cold"),
    ("Kinetic High-Support Bra", "Sports Bras", "Running", "bra", 2599, None, ["Onyx", "Graphite", "Bone"], WIDE, "N",
     "High-impact support engineered for running. Adjustable straps, encapsulated cups and a no-slip band keep you secure.",
     "Fabric: 78% recycled nylon, 22% elastane\nSupport: High\nWeight: 210 gsm\nFeatures: Adjustable straps, hook-and-eye back\nCare: Machine wash cold"),
    ("Flow Yoga Tank", "Tops", "Yoga", "tank", 1899, None, ["Bone", "Clay", "Fog"], WIDE, "",
     "A cropped, buttery-soft tank for the mat. Breathable and drapey, it moves through every flow without a distraction.",
     "Fabric: 85% modal, 15% elastane\nFit: Relaxed crop\nWeight: 150 gsm\nFeatures: Raw hem, soft-touch finish\nCare: Machine wash cold"),
    ("Summit Thermal Jacket", "Outerwear", "Cycling", "jacket", 6299, None, ["Onyx", "Navy"], STD, "",
     "Insulated thermal jacket for deep-winter rides and runs. Windproof front panels with a stretch back for ventilation.",
     "Fabric: Softshell with thermal grid lining\nFit: Athletic\nWeight: 310 gsm\nFeatures: Windproof front, 3 zip pockets\nCare: Machine wash cold"),
]


def seed_all(quiet=False):
    log = (lambda *a: None) if quiet else print
    if Product.query.count() == 0:
        cats = {}
        for n in CATEGORIES:
            c = Category.query.filter_by(name=n).first() or Category(name=n, slug=n.lower().replace(" ", "-"))
            db.session.add(c); cats[n] = c
        rng = random.Random(42)
        for name, cat, sport, garment, price, cmp_, cols, sizes, flags, desc, specs in P:
            p = Product(name=name, slug=name.lower().replace('"', "").replace(" ", "-"), category=cats[cat],
                        sport=sport, garment=garment, price=price, compare_at_price=cmp_,
                        featured="F" in flags, bestseller="B" in flags, is_new="N" in flags,
                        description=desc, specs=specs)
            for col in cols:
                for s in sizes:
                    p.variants.append(ProductVariant(size=s, color_name=col, color_hex=COLORS[col],
                                                     stock=rng.choice([0, 3, 8, 14, 20, 25]) if rng.random() < .12 else rng.randint(6, 30),
                                                     sku=f"KV-{p.slug[:8].upper()}-{s}-{col[:3].upper()}"))
            db.session.add(p)
        db.session.commit()
        log(f"Seeded {len(P)} products.")

    email, pw = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    prod = os.environ.get("FLASK_ENV") == "production"
    if not email and not prod:
        email, pw = "admin@korva.example", "Admin#12345"
    if email and pw and not User.query.filter_by(email=email.lower()).first():
        u = User(name="KORVA Admin", email=email.lower(), is_admin=True)
        u.set_password(pw)
        db.session.add(u); db.session.commit()
        log(f"Admin created: {email}")

    if not prod and Order.query.count() == 0:
        _demo_orders()
        log("Demo customer + orders created (demo@korva.example / Demo#12345).")


def _demo_orders():
    cust = User.query.filter_by(email="demo@korva.example").first()
    if not cust:
        cust = User(name="Demo Customer", email="demo@korva.example", phone="9876543210")
        cust.set_password("Demo#12345")
        db.session.add(cust); db.session.commit()
    rng = random.Random(7)
    variants = ProductVariant.query.filter(ProductVariant.stock > 5).all()
    statuses = ["Delivered", "Delivered", "Shipped", "Processing", "Paid", "Paid", "Pending", "Delivered", "Cancelled"]
    for i, st in enumerate(statuses * 2):
        picks = rng.sample(variants, rng.randint(1, 3))
        o = Order(number=f"KV-DEMO-{1000 + i}", user_id=cust.id, status=st, subtotal=0, shipping=0, total=0,
                  ship_name=cust.name, ship_email=cust.email, ship_phone="9876543210", ship_address="12 MG Road",
                  ship_city="Bengaluru", ship_state="Karnataka", ship_postal="560001",
                  created_at=utcnow() - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 20)))
        sub = 0
        for v in picks:
            q = rng.randint(1, 2); sub += float(v.product.price) * q
            o.items.append(OrderItem(variant_id=v.id, product_id=v.product_id, product_name=v.product.name,
                                     garment=v.product.garment, size=v.size, color_name=v.color_name,
                                     color_hex=v.color_hex, unit_price=v.product.price, quantity=q))
        ship = 0 if sub >= 5000 else 199
        o.subtotal, o.shipping, o.total = sub, ship, sub + ship
        o.payment = Payment(provider="mock", method="card", reference=f"MOCK_DEMO{i}", amount=o.total,
                            status="succeeded" if st != "Pending" else "pending")
        db.session.add(o)
    db.session.commit()
