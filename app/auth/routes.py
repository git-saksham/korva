from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, RegisterForm
from ..models import User
from ..services.cart import merge_guest_cart

bp = Blueprint("auth", __name__)


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*a, **kw):
        if not current_user.is_admin:
            abort(403)
        return fn(*a, **kw)
    return wrapper


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            merge_guest_cart(user)
            return redirect(safe_next(request.args.get("next")) or (url_for("admin.dashboard") if user.is_admin else url_for("account.account")))
        flash("Incorrect email or password.", "danger")
    return render_template("auth/login.html", form=form, mode="login", register_form=RegisterForm())


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        merge_guest_cart(user)
        flash("Welcome to KORVA.", "success")
        return redirect(safe_next(request.args.get("next")) or url_for("account.account"))
    return render_template("auth/login.html", form=LoginForm(), register_form=form, mode="register")


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("main.home"))
