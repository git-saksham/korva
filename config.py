import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_uri() -> str:
    uri = os.environ.get("DATABASE_URL")
    if uri:
        # Heroku/Render style URLs
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    if os.environ.get("VERCEL"):  # read-only FS: only /tmp is writable (demo only)
        return "sqlite:///" + os.path.join(tempfile.gettempdir(), "korva.db")
    return "sqlite:///" + os.path.join(BASE_DIR, "korva.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-insecure-key-change-me"
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    WTF_CSRF_TIME_LIMIT = None

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    UPLOAD_FOLDER = (
        os.path.join(tempfile.gettempdir(), "korva-uploads")
        if os.environ.get("VERCEL")
        else os.path.join(BASE_DIR, "app", "static", "uploads")
    )

    BRAND = "KORVA"
    CURRENCY = "₹"
    FREE_SHIPPING_THRESHOLD = 5000
    SHIPPING_FLAT = 199
    LOW_STOCK_THRESHOLD = 5

    PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")
    AUTO_SEED = os.environ.get("AUTO_SEED") == "1"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
    SESSION_COOKIE_SECURE = False
