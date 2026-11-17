from flask import Blueprint, jsonify, render_template, request

from ..extensions import db
from ..models import CartItem, Product, ProductVariant
from ..services.cart import cart_issues, get_cart, totals

bp = Blueprint("cart", __name__)
MAX_QTY = 10


def _payload(msg=None, ok=True, status=200, **extra):
    cart = get_cart(create=False)
    t = totals(cart)
    html = render_template("partials/cart_drawer_body.html", cart=cart, t=t, issues=cart_issues(cart) if cart else [])
    return jsonify(ok=ok, message=msg, count=cart.count if cart else 0, html=html,
                   subtotal=float(t["subtotal"]), **extra), status


def _int(v, default=1):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@bp.route("/cart")
def view():
    cart = get_cart(create=False)
    return render_template("cart.html", cart=cart, t=totals(cart), issues=cart_issues(cart) if cart else [])


@bp.route("/cart/state")
def state():
    return _payload()


@bp.route("/cart/add", methods=["POST"])
def add():
    data = request.get_json(silent=True) or request.form
    qty = max(1, min(_int(data.get("quantity"), 1), MAX_QTY))
    variant = None
    if data.get("variant_id"):
        variant = db.session.get(ProductVariant, _int(data.get("variant_id"), 0))
    elif data.get("product_id") and data.get("size"):  # quick-add from grid
        q = ProductVariant.query.filter_by(product_id=_int(data.get("product_id"), 0), size=data.get("size")) \
            .filter(ProductVariant.stock > 0)
        if data.get("color"):
            q = q.filter_by(color_name=data.get("color"))
        variant = q.order_by(ProductVariant.id).first()
    if not variant or not variant.product.is_active:
        return _payload("That option isn't available.", ok=False, status=400)
    if variant.stock <= 0:
        return _payload("Sorry, that size/colour is sold out.", ok=False, status=409)
    cart = get_cart()
    item = next((i for i in cart.items if i.variant_id == variant.id), None)
    new_qty = (item.quantity if item else 0) + qty
    if new_qty > variant.stock:
        return _payload(f"Only {variant.stock} in stock.", ok=False, status=409)
    new_qty = min(new_qty, MAX_QTY)
    if item:
        item.quantity = new_qty
    else:
        cart.items.append(CartItem(variant_id=variant.id, quantity=new_qty))
    db.session.commit()
    return _payload(f"Added {variant.product.name} — {variant.size}", open_drawer=True)


@bp.route("/cart/update", methods=["POST"])
def update():
    data = request.get_json(silent=True) or request.form
    cart = get_cart()
    item = next((i for i in cart.items if i.id == _int(data.get("item_id"), 0)), None)
    if not item:
        return _payload("Item not found.", ok=False, status=404)
    qty = _int(data.get("quantity"), item.quantity)
    if qty <= 0:
        db.session.delete(item)
    else:
        qty = min(qty, MAX_QTY)
        if qty > item.variant.stock:
            return _payload(f"Only {item.variant.stock} in stock.", ok=False, status=409)
        item.quantity = qty
    db.session.commit()
    return _payload()


@bp.route("/cart/remove", methods=["POST"])
def remove():
    data = request.get_json(silent=True) or request.form
    cart = get_cart()
    item = next((i for i in cart.items if i.id == _int(data.get("item_id"), 0)), None)
    if item:
        db.session.delete(item)
        db.session.commit()
    return _payload("Removed from bag")
