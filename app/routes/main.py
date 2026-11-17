from flask import (Blueprint, Response, abort, current_app, jsonify, render_template, request)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (Category, OrderItem, Product, ProductVariant, SIZES, SPORTS, WishlistItem)
from ..services import recommender
from ..services.art import garment_svg, hero_svg

bp = Blueprint("main", __name__)

SORTS = {
    "featured": (Product.featured.desc(), Product.id.desc()),
    "newest": (Product.created_at.desc(), Product.id.desc()),
    "price_asc": (Product.price.asc(),),
    "price_desc": (Product.price.desc(),),
    "name": (Product.name.asc(),),
}


def _cached(svg):
    r = Response(svg, mimetype="image/svg+xml")
    r.headers["Cache-Control"] = "public, max-age=604800"
    return r


@bp.route("/art/<garment>/<hex_color>.svg")
def garment_art(garment, hex_color):
    if not (len(hex_color) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in hex_color)):
        abort(404)
    return _cached(garment_svg(garment, hex_color))


@bp.route("/art/hero.svg")
def hero_art():
    return _cached(hero_svg())


@bp.route("/")
def home():
    featured = Product.query.filter_by(is_active=True, featured=True).order_by(Product.id).limit(4).all()
    best = bestsellers(4)
    recs = recommender.for_user(current_user, 4) or Product.query.filter_by(is_active=True, is_new=True).limit(4).all()
    cats = []
    for sport in ["Running", "Training", "Yoga", "Cycling"]:
        n = Product.query.filter_by(is_active=True, sport=sport).count()
        p = Product.query.filter_by(is_active=True, sport=sport).order_by(Product.featured.desc()).first()
        if p:
            cats.append({"sport": sport, "count": n, "product": p})
    return render_template("home.html", featured=featured, best=best, recs=recs, sport_tiles=cats,
                           personalised=current_user.is_authenticated and bool(recommender.for_user(current_user, 1)))


def bestsellers(n):
    sold = (db.session.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("q"))
            .group_by(OrderItem.product_id).order_by(func.sum(OrderItem.quantity).desc()).limit(n).all())
    flagged = Product.query.filter_by(is_active=True, bestseller=True).order_by(Product.id).all()
    out, seen = [], set()
    for p in flagged:
        out.append(p); seen.add(p.id)
    for pid, _ in sold:
        p = db.session.get(Product, pid)
        if p and p.is_active and p.id not in seen:
            out.append(p); seen.add(p.id)
    return out[:n]


@bp.route("/shop")
def shop():
    args = request.args
    q = Product.query.filter_by(is_active=True)
    term = args.get("q", "").strip()
    if term:
        like = f"%{term}%"
        q = q.join(Category).filter(or_(Product.name.ilike(like), Product.description.ilike(like),
                                        Product.sport.ilike(like), Category.name.ilike(like)))
    cat = args.get("category")
    if cat:
        q = q.filter(Product.category.has(Category.slug == cat))
    sport = args.get("sport")
    if sport:
        q = q.filter(Product.sport == sport)
    size = args.get("size")
    if size in SIZES:
        q = q.filter(Product.variants.any(db.and_(ProductVariant.size == size, ProductVariant.stock > 0)))
    for key, op in (("min", "ge"), ("max", "le")):
        try:
            val = float(args.get(key, ""))
            q = q.filter(getattr(Product.price, f"__{op}__")(val))
        except ValueError:
            pass
    sort = args.get("sort", "featured")
    q = q.order_by(*SORTS.get(sort, SORTS["featured"]))
    products = q.all()
    ctx = dict(products=products, categories=Category.query.order_by(Category.name).all(),
               sports=SPORTS, sizes=SIZES, f=args, term=term, sort=sort)
    if request.args.get("partial"):
        return render_template("partials/shop_results.html", **ctx)
    return render_template("shop.html", **ctx)


@bp.route("/api/search")
def api_search():
    term = request.args.get("q", "").strip()
    if len(term) < 2:
        return jsonify(results=[])
    like = f"%{term}%"
    rows = (Product.query.filter_by(is_active=True)
            .filter(or_(Product.name.ilike(like), Product.sport.ilike(like))).limit(6).all())
    return jsonify(results=[{"name": p.name, "url": f"/product/{p.slug}", "img": p.image_url(),
                             "price": f"{current_app.config['CURRENCY']}{p.price:,.0f}"} for p in rows])


@bp.route("/product/<slug>")
def product(slug):
    p = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    related = recommender.similar_to(p.id, 4)
    variants = [{"id": v.id, "size": v.size, "color": v.color_name, "hex": v.color_hex, "stock": v.stock}
                for v in p.variants]
    return render_template("product.html", p=p, related=related, variants=variants)


@bp.route("/wishlist/toggle/<int:pid>", methods=["POST"])
def wishlist_toggle(pid):
    if not current_user.is_authenticated:
        return jsonify(ok=False, login=True, error="Sign in to save favourites."), 401
    db.get_or_404(Product, pid)
    item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if item:
        db.session.delete(item); saved = False
    else:
        db.session.add(WishlistItem(user_id=current_user.id, product_id=pid)); saved = True
    db.session.commit()
    return jsonify(ok=True, saved=saved, message="Saved to favourites" if saved else "Removed from favourites")
