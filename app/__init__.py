import os
from decimal import Decimal

import click
from flask import Flask, render_template, request, jsonify

from config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if app.config.get("SECRET_KEY") == "dev-insecure-key-change-me" and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("Set a strong SECRET_KEY in production.")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .routes.main import bp as main_bp
    from .routes.cart import bp as cart_bp
    from .routes.shop_account import checkout_bp, account_bp
    from .auth.routes import bp as auth_bp
    from .admin.routes import bp as admin_bp

    for bp in (main_bp, cart_bp, checkout_bp, account_bp, auth_bp, admin_bp):
        app.register_blueprint(bp)

    @app.template_filter("money")
    def money(v):
        v = Decimal(v or 0)
        txt = f"{v:,.0f}" if v == v.to_integral_value() else f"{v:,.2f}"
        return f"{app.config['CURRENCY']}{txt}"

    @app.context_processor
    def inject():
        from flask_login import current_user
        from .services.cart import get_cart
        cart = get_cart(create=False)
        wish = current_user.wishlist_ids if current_user.is_authenticated else set()
        return {
            "BRAND": app.config["BRAND"],
            "cart_count": cart.count if cart else 0,
            "wish_ids": wish,
            "FREE_SHIP": app.config["FREE_SHIPPING_THRESHOLD"],
        }

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    def wants_json():
        return request.path.startswith(("/cart/", "/wishlist/", "/api/", "/admin/variants"))

    @app.errorhandler(404)
    def nf(e):
        if wants_json():
            return jsonify(ok=False, error="Not found"), 404
        return render_template("error.html", code=404, msg="This page is out of bounds."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, msg="You don't have access to this area."), 403

    @app.errorhandler(400)
    def bad(e):
        if wants_json():
            return jsonify(ok=False, error=getattr(e, "description", "Bad request")), 400
        return render_template("error.html", code=400, msg="That request could not be completed. Refresh and try again."), 400

    @app.errorhandler(500)
    def err(e):
        db.session.rollback()
        return render_template("error.html", code=500, msg="Something went wrong on our side."), 500

    register_cli(app)

    with app.app_context():
        if app.config.get("AUTO_SEED"):
            db.create_all()
            from seed.seed import seed_all
            seed_all(quiet=True)
    return app


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Drop everything first.")
    def seed(reset):
        """Create tables and load the demo catalogue."""
        from seed.seed import seed_all
        if reset:
            db.drop_all()
        db.create_all()
        seed_all()

    @app.cli.command("create-admin")
    @click.option("--email", default=lambda: os.environ.get("ADMIN_EMAIL"))
    @click.option("--password", default=lambda: os.environ.get("ADMIN_PASSWORD"))
    @click.option("--name", default="Admin")
    def create_admin(email, password, name):
        """Create or promote an admin user."""
        from .models import User
        if not email or not password:
            raise click.UsageError("Provide --email/--password or set ADMIN_EMAIL / ADMIN_PASSWORD.")
        db.create_all()
        u = User.query.filter_by(email=email.lower()).first() or User(email=email.lower(), name=name)
        u.set_password(password)
        u.is_admin = True
        db.session.add(u)
        db.session.commit()
        click.echo(f"Admin ready: {email}")
