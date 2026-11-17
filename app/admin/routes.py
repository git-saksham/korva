import os
import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for)
from flask_login import current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from ..auth.routes import admin_required
from ..extensions import db
from ..models import (GARMENTS, ORDER_STATUSES, SIZES, SPORTS, CartItem, Category, Order, OrderItem, Product,
                      ProductVariant, User, utcnow)

bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_IMG = {"png", "jpg", "jpeg", "webp"}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


@bp.route("/")
@admin_required
def dashboard():
    tab = request.args.get("tab", "overview")
    low = current_app.config["LOW_STOCK_THRESHOLD"]
    paid = Order.status.notin_(["Cancelled", "Pending"])
    revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(paid).scalar()
    stats = {
        "products": Product.query.count(),
        "users": User.query.count(),
        "orders": Order.query.count(),
        "revenue": revenue,
    }
    # last 14 days of revenue for the chart
    start = (utcnow() - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
    recent = Order.query.filter(Order.created_at >= start, paid).all()
    days = [(start + timedelta(days=i)).date() for i in range(14)]
    series = {d: Decimal(0) for d in days}
    for o in recent:
        series[o.created_at.date()] = series.get(o.created_at.date(), Decimal(0)) + o.total
    peak = max(series.values()) or Decimal(1)
    chart = [{"label": d.strftime("%d %b"), "value": float(v), "pct": float(v / peak * 100)} for d, v in series.items()]

    low_stock = (ProductVariant.query.filter(ProductVariant.stock <= low).join(Product)
                 .filter(Product.is_active).order_by(ProductVariant.stock, ProductVariant.id).all())
    ctx = dict(tab=tab, stats=stats, chart=chart, low_stock=low_stock, low=low,
               recent_orders=Order.query.order_by(Order.created_at.desc()).limit(6).all(),
               statuses=ORDER_STATUSES)
    if tab == "products":
        ctx["products"] = Product.query.order_by(Product.id.desc()).all()
        ctx["categories"] = Category.query.order_by(Category.name).all()
    elif tab == "inventory":
        ctx["variants"] = (ProductVariant.query.join(Product).order_by(Product.name, ProductVariant.color_name,
                                                                       ProductVariant.id).all())
    elif tab == "orders":
        ctx["orders"] = Order.query.order_by(Order.created_at.desc()).limit(200).all()
    elif tab == "users":
        counts = dict(db.session.query(Order.user_id, func.count(Order.id)).group_by(Order.user_id).all())
        ctx["users"] = User.query.order_by(User.created_at.desc()).all()
        ctx["order_counts"] = counts
    return render_template("admin/dashboard.html", **ctx)


# ---- products ----------------------------------------------------------------
def _form_ctx(product):
    return dict(p=product, categories=Category.query.order_by(Category.name).all(), sports=SPORTS,
                garments=GARMENTS, all_sizes=SIZES)


@bp.route("/products/form", defaults={"pid": None})
@bp.route("/products/<int:pid>/form")
@admin_required
def product_form(pid):
    p = db.session.get(Product, pid) if pid else None
    stock = {}
    if p:
        stock = {f"{v.size}__{v.color_name}": v.stock for v in p.variants}
    return render_template("admin/product_form.html", stock=stock, **_form_ctx(p))


def _save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMG:
        raise ValueError("Image must be PNG, JPG or WEBP.")
    from PIL import Image
    try:
        Image.open(file_storage.stream).verify()
    except Exception:
        raise ValueError("That file isn't a valid image.")
    file_storage.stream.seek(0)
    name = f"{secrets.token_hex(8)}-{secure_filename(file_storage.filename)}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return f"uploads/{name}"


def _dec(v, default=None):
    try:
        d = Decimal(str(v).strip())
        return d if d >= 0 else default
    except (InvalidOperation, AttributeError):
        return default


@bp.route("/products/save", methods=["POST"])
@admin_required
def product_save():
    f = request.form
    pid = f.get("id")
    p = db.session.get(Product, int(pid)) if pid else Product()
    name = f.get("name", "").strip()
    price = _dec(f.get("price"))
    cat = db.session.get(Category, int(f.get("category_id") or 0))
    if not name or price is None or not cat:
        flash("Name, a valid price and a category are required.", "danger")
        return redirect(url_for("admin.dashboard", tab="products"))
    p.name, p.price = name, price
    p.compare_at_price = _dec(f.get("compare_at_price"))
    p.sport = f.get("sport") if f.get("sport") in SPORTS else "Training"
    p.garment = f.get("garment") if f.get("garment") in GARMENTS else "tee"
    p.description = f.get("description", "").strip()
    p.specs = f.get("specs", "").strip()
    p.featured, p.bestseller = bool(f.get("featured")), bool(f.get("bestseller"))
    p.is_new, p.is_active = bool(f.get("is_new")), bool(f.get("is_active"))
    try:
        img = _save_image(request.files.get("image"))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("admin.dashboard", tab="products"))
    if img:
        p.image_path = img
    elif f.get("image_url", "").strip().startswith("https://"):
        p.image_path = f.get("image_url").strip()
    elif f.get("clear_image"):
        p.image_path = None
    if not p.id:
        base = slugify(name); slug, n = base, 2
        while Product.query.filter_by(slug=slug).first():
            slug, n = f"{base}-{n}", n + 1
        p.slug = slug
    p.category = cat
    db.session.add(p)

    # variants = sizes x colours (+ per-variant stock)
    sizes = [s for s in f.getlist("sizes") if s in SIZES]
    names, hexes = f.getlist("color_name"), f.getlist("color_hex")
    colours = []
    for n_, h_ in zip(names, hexes):
        n_, h_ = n_.strip(), h_.strip()
        if n_ and re.fullmatch(r"#[0-9a-fA-F]{6}", h_):
            colours.append((n_, h_.lower()))
    wanted = {(s, n_): h_ for s in sizes for n_, h_ in colours}
    existing = {(v.size, v.color_name): v for v in p.variants}
    for key, v in existing.items():
        if key not in wanted:
            CartItem.query.filter_by(variant_id=v.id).delete()
            OrderItem.query.filter_by(variant_id=v.id).update({"variant_id": None})
            db.session.delete(v)
    for (s, n_), h_ in wanted.items():
        try:
            stock = max(0, int(f.get(f"stock__{s}__{n_}", 0) or 0))
        except ValueError:
            stock = 0
        v = existing.get((s, n_))
        if v:
            v.color_hex, v.stock = h_, stock
        else:
            p.variants.append(ProductVariant(size=s, color_name=n_, color_hex=h_, stock=stock,
                                             sku=f"KV-{slugify(name)[:10].upper()}-{s}-{slugify(n_)[:4].upper()}"))
    db.session.commit()
    flash(f"Saved “{p.name}”.", "success")
    return redirect(url_for("admin.dashboard", tab="products"))


@bp.route("/products/<int:pid>/delete", methods=["POST"])
@admin_required
def product_delete(pid):
    p = db.get_or_404(Product, pid)
    for v in p.variants:
        CartItem.query.filter_by(variant_id=v.id).delete()
        OrderItem.query.filter_by(variant_id=v.id).update({"variant_id": None})
    from ..models import WishlistItem
    WishlistItem.query.filter_by(product_id=p.id).delete()
    name = p.name
    db.session.delete(p)
    db.session.commit()
    flash(f"Deleted “{name}”.", "info")
    return redirect(url_for("admin.dashboard", tab="products"))


# ---- inventory ---------------------------------------------------------------
@bp.route("/variants/<int:vid>/stock", methods=["POST"])
@admin_required
def variant_stock(vid):
    v = db.get_or_404(ProductVariant, vid)
    data = request.get_json(silent=True) or request.form
    try:
        stock = int(data.get("stock"))
        if stock < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Stock must be a non-negative whole number."), 400
    v.stock = stock
    db.session.commit()
    return jsonify(ok=True, stock=v.stock, low=v.stock <= current_app.config["LOW_STOCK_THRESHOLD"])


# ---- orders -------------------------------------------------------------------
@bp.route("/orders/<int:oid>")
@admin_required
def order_fragment(oid):
    return render_template("admin/order_fragment.html", order=db.get_or_404(Order, oid), statuses=ORDER_STATUSES)


@bp.route("/orders/<int:oid>/status", methods=["POST"])
@admin_required
def order_status(oid):
    o = db.get_or_404(Order, oid)
    new = request.form.get("status") or (request.get_json(silent=True) or {}).get("status")
    if new not in ORDER_STATUSES:
        return jsonify(ok=False, error="Invalid status"), 400
    # Restock when cancelling an order that had reserved stock.
    if new == "Cancelled" and o.status != "Cancelled":
        for it in o.items:
            if it.variant_id:
                v = db.session.get(ProductVariant, it.variant_id)
                if v:
                    v.stock += it.quantity
    elif o.status == "Cancelled" and new != "Cancelled":
        for it in o.items:
            v = db.session.get(ProductVariant, it.variant_id) if it.variant_id else None
            if v:
                v.stock = max(0, v.stock - it.quantity)
    o.status = new
    if new == "Paid" and o.payment:
        o.payment.status = "succeeded"
    db.session.commit()
    if request.is_json:
        return jsonify(ok=True, status=o.status)
    flash(f"Order {o.number} → {new}", "success")
    return redirect(url_for("admin.dashboard", tab="orders"))
