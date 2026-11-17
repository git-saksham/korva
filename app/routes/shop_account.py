import secrets
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import CheckoutForm, ProfileForm
from ..models import Order, OrderItem, Payment, ProductVariant, WishlistItem, utcnow
from ..services.cart import cart_issues, get_cart, totals
from ..services.payments import METHODS, get_gateway

checkout_bp = Blueprint("checkout", __name__)
account_bp = Blueprint("account", __name__)


def _order_number():
    return "KV-" + utcnow().strftime("%y%m%d") + "-" + secrets.token_hex(3).upper()


@checkout_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = get_cart(create=False)
    if not cart or not cart.items:
        flash("Your bag is empty.", "info")
        return redirect(url_for("main.shop"))
    issues = cart_issues(cart)
    form = CheckoutForm(request.form if request.method == "POST" else None)
    if request.method == "GET":
        form.name.data, form.email.data, form.phone.data = current_user.name, current_user.email, current_user.phone or ""
        form.method.data = "card"

    if request.method == "POST" and form.validate():
        if issues:
            for i in issues:
                flash(i, "danger")
            return redirect(url_for("cart.view"))
        # Lock rows (no-op on SQLite) and re-validate stock inside the transaction.
        ids = [i.variant_id for i in cart.items]
        locked = {v.id: v for v in ProductVariant.query.filter(ProductVariant.id.in_(ids)).with_for_update().all()}
        for it in cart.items:
            if locked[it.variant_id].stock < it.quantity:
                flash(f"Stock changed for {it.variant.product.name} ({it.variant.size}).", "danger")
                return redirect(url_for("cart.view"))
        t = totals(cart)  # prices always come from the database, never the client
        gateway = get_gateway(current_app)
        result = gateway.charge(t["total"], form.method.data, {
            "card_number": form.card_number.data or "", "upi_id": form.upi_id.data or ""})
        if not result.success:
            flash(result.message, "danger")
            return render_template("checkout.html", form=form, cart=cart, t=t, methods=METHODS, issues=issues), 402

        order = Order(number=_order_number(), user_id=current_user.id,
                      status="Paid" if result.status == "succeeded" else "Pending",
                      subtotal=t["subtotal"], shipping=t["shipping"], total=t["total"],
                      ship_name=form.name.data.strip(), ship_email=form.email.data.strip(),
                      ship_phone=form.phone.data.strip(), ship_address=form.address.data.strip(),
                      ship_city=form.city.data.strip(), ship_state=form.state.data.strip(),
                      ship_postal=form.postal.data.strip())
        for it in cart.items:
            v = locked[it.variant_id]
            v.stock -= it.quantity
            order.items.append(OrderItem(variant_id=v.id, product_id=v.product_id, product_name=v.product.name,
                                         garment=v.product.garment, size=v.size, color_name=v.color_name,
                                         color_hex=v.color_hex, unit_price=v.product.price, quantity=it.quantity))
        order.payment = Payment(provider=gateway.name, method=form.method.data, reference=result.reference,
                                amount=t["total"], status=result.status)
        db.session.add(order)
        for it in list(cart.items):
            db.session.delete(it)
        if not current_user.phone:
            current_user.phone = form.phone.data.strip()
        db.session.commit()
        return redirect(url_for("account.order_detail", number=order.number, placed=1))
    return render_template("checkout.html", form=form, cart=cart, t=totals(cart), methods=METHODS, issues=issues)


@account_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account.account"))
    favs = [w.product for w in sorted(current_user.wishlist, key=lambda w: w.created_at, reverse=True)]
    return render_template("account/account.html", form=form, orders=current_user.orders, favs=favs)


@account_bp.route("/account/orders/<number>")
@login_required
def order_detail(number):
    order = Order.query.filter_by(number=number).first_or_404()
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(404)
    return render_template("account/order.html", order=order, placed=request.args.get("placed"))
