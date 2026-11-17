"""Relational schema for the KORVA store."""
from datetime import datetime, timezone
from decimal import Decimal

from flask import url_for
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

ORDER_STATUSES = ["Pending", "Paid", "Processing", "Shipped", "Delivered", "Cancelled"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SPORTS = ["Running", "Training", "Yoga", "Cycling", "Basketball", "Lifestyle"]
GARMENTS = ["tee", "tank", "shorts", "pants", "jacket", "hoodie", "compression", "bra"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(32))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    orders = db.relationship("Order", back_populates="user", order_by="Order.created_at.desc()")
    wishlist = db.relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def wishlist_ids(self):
        return {w.product_id for w in self.wishlist}


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default="")
    specs = db.Column(db.Text, default="")  # "Label: value" per line
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_at_price = db.Column(db.Numeric(10, 2))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    sport = db.Column(db.String(40), default="Training", index=True)
    garment = db.Column(db.String(20), default="tee")
    image_path = db.Column(db.String(255))  # uploaded image; falls back to generated art
    featured = db.Column(db.Boolean, default=False)
    bestseller = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    category = db.relationship("Category", back_populates="products")
    variants = db.relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan",
        order_by="ProductVariant.id",
    )

    # ---- helpers -------------------------------------------------------
    @property
    def colors(self):
        seen, out = set(), []
        for v in self.variants:
            if v.color_hex not in seen:
                seen.add(v.color_hex)
                out.append({"name": v.color_name, "hex": v.color_hex})
        return out

    @property
    def sizes(self):
        present = {v.size for v in self.variants}
        return [s for s in SIZES if s in present]

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants)

    @property
    def in_stock(self):
        return self.total_stock > 0

    def sizes_in_stock(self):
        have = {v.size for v in self.variants if v.stock > 0}
        return [s for s in self.sizes if s in have]

    def image_url(self, hex_color=None):
        if self.image_path:
            return self.image_path if self.image_path.startswith("http") else url_for("static", filename=self.image_path)
        hex_color = (hex_color or (self.colors[0]["hex"] if self.colors else "#2a2a2c")).lstrip("#")
        return url_for("main.garment_art", garment=self.garment, hex_color=hex_color)

    @property
    def spec_pairs(self):
        pairs = []
        for line in (self.specs or "").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                pairs.append((k.strip(), v.strip()))
        return pairs

    @property
    def price_f(self):
        return Decimal(self.price)


class ProductVariant(db.Model):
    __tablename__ = "product_variants"
    __table_args__ = (db.UniqueConstraint("product_id", "size", "color_name", name="uq_variant"),)
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    size = db.Column(db.String(8), nullable=False)
    color_name = db.Column(db.String(40), nullable=False)
    color_hex = db.Column(db.String(9), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    sku = db.Column(db.String(40))

    product = db.relationship("Product", back_populates="variants")


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    token = db.Column(db.String(64), index=True)  # guest carts
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan",
                            order_by="CartItem.id")

    @property
    def count(self):
        return sum(i.quantity for i in self.items)

    @property
    def subtotal(self):
        return sum((Decimal(i.variant.product.price) * i.quantity for i in self.items), Decimal(0))


class CartItem(db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (db.UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),)
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    cart = db.relationship("Cart", back_populates="items")
    variant = db.relationship("ProductVariant")

    @property
    def line_total(self):
        return Decimal(self.variant.product.price) * self.quantity


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_wish"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User", back_populates="wishlist")
    product = db.relationship("Product")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(24), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    ship_name = db.Column(db.String(120))
    ship_email = db.Column(db.String(255))
    ship_phone = db.Column(db.String(32))
    ship_address = db.Column(db.String(255))
    ship_city = db.Column(db.String(80))
    ship_state = db.Column(db.String(80))
    ship_postal = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = db.relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="SET NULL"))
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(160), nullable=False)  # snapshot
    garment = db.Column(db.String(20))
    size = db.Column(db.String(8))
    color_name = db.Column(db.String(40))
    color_hex = db.Column(db.String(9))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order = db.relationship("Order", back_populates="items")

    @property
    def line_total(self):
        return Decimal(self.unit_price) * self.quantity


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, unique=True)
    provider = db.Column(db.String(30), nullable=False)
    method = db.Column(db.String(30))
    reference = db.Column(db.String(80))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending / succeeded / failed
    created_at = db.Column(db.DateTime, default=utcnow)
    order = db.relationship("Order", back_populates="payment")
