import secrets
from decimal import Decimal

from flask import current_app, session
from flask_login import current_user

from ..extensions import db
from ..models import Cart, CartItem, ProductVariant


def get_cart(create=True):
    if current_user.is_authenticated:
        cart = Cart.query.filter_by(user_id=current_user.id).first()
        if not cart and create:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.flush()
        return cart
    token = session.get("cart_token")
    cart = Cart.query.filter_by(token=token, user_id=None).first() if token else None
    if not cart and create:
        token = secrets.token_hex(16)
        session["cart_token"] = token
        cart = Cart(token=token)
        db.session.add(cart)
        db.session.flush()
    return cart


def merge_guest_cart(user):
    token = session.pop("cart_token", None)
    if not token:
        return
    guest = Cart.query.filter_by(token=token, user_id=None).first()
    if not guest:
        return
    mine = Cart.query.filter_by(user_id=user.id).first() or Cart(user_id=user.id)
    db.session.add(mine)
    db.session.flush()
    existing = {i.variant_id: i for i in mine.items}
    for it in list(guest.items):
        if it.variant_id in existing:
            existing[it.variant_id].quantity = min(existing[it.variant_id].quantity + it.quantity, 10)
        else:
            mine.items.append(CartItem(variant_id=it.variant_id, quantity=it.quantity))
    db.session.delete(guest)
    db.session.commit()


def shipping_for(subtotal: Decimal) -> Decimal:
    if subtotal <= 0 or subtotal >= current_app.config["FREE_SHIPPING_THRESHOLD"]:
        return Decimal(0)
    return Decimal(current_app.config["SHIPPING_FLAT"])


def cart_issues(cart):
    """Server-side stock validation. Returns list of human readable problems."""
    problems = []
    for it in cart.items:
        v = it.variant
        label = f"{v.product.name} ({v.color_name} / {v.size})"
        if not v.product.is_active:
            problems.append(f"{label} is no longer available.")
        elif v.stock <= 0:
            problems.append(f"{label} is out of stock.")
        elif it.quantity > v.stock:
            problems.append(f"Only {v.stock} left of {label}.")
    return problems


def totals(cart):
    subtotal = cart.subtotal if cart else Decimal(0)
    shipping = shipping_for(subtotal)
    return {"subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping}
