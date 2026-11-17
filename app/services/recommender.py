"""Content-based recommendations: TF-IDF over name/category/sport/description + cosine similarity."""
import threading

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from ..extensions import db
from ..models import Product

_lock = threading.Lock()
_cache = {"key": None, "df": None, "sim": None}


def _signature():
    rows = db.session.query(Product.id, Product.name, Product.sport, Product.category_id,
                            Product.is_active, Product.description).all()
    return hash(tuple(rows))


def _build():
    products = Product.query.filter_by(is_active=True).all()
    df = pd.DataFrame([
        {
            "id": p.id,
            "text": " ".join([
                p.name, p.name, p.category.name, p.category.name,
                p.sport or "", p.sport or "", p.garment or "", p.description or "",
            ]).lower(),
        }
        for p in products
    ])
    if df.empty:
        return df, np.zeros((0, 0))
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = tfidf.fit_transform(df["text"])
    return df, linear_kernel(matrix, matrix)


def _model():
    key = _signature()
    with _lock:
        if _cache["key"] != key:
            _cache["df"], _cache["sim"] = _build()
            _cache["key"] = key
        return _cache["df"], _cache["sim"]


def similar_to(product_id: int, n: int = 4):
    df, sim = _model()
    idx = df.index[df["id"] == product_id]
    if len(idx) == 0:
        return []
    scores = sim[idx[0]].copy()
    scores[idx[0]] = -1
    top = np.argsort(scores)[::-1][:n]
    ids = [int(df.iloc[i]["id"]) for i in top if scores[i] > 0]
    return _load(ids)


def for_user(user, n: int = 4):
    """Profile = mean similarity to wishlisted / purchased products."""
    seed = set()
    if user is not None and user.is_authenticated:
        seed |= {w.product_id for w in user.wishlist}
        for o in user.orders[:5]:
            seed |= {i.product_id for i in o.items if i.product_id}
    df, sim = _model()
    idx = [df.index[df["id"] == pid][0] for pid in seed if (df["id"] == pid).any()]
    if not idx:
        return []
    scores = sim[idx].mean(axis=0)
    scores[idx] = -1
    top = np.argsort(scores)[::-1][:n]
    return _load([int(df.iloc[i]["id"]) for i in top if scores[i] > 0])


def _load(ids):
    if not ids:
        return []
    by_id = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()}
    return [by_id[i] for i in ids if i in by_id]
