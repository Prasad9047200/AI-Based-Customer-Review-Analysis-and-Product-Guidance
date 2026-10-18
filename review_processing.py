"""
Review Processing Module
Handles loading, filtering, and NLP pre-processing of review data.
Also computes local statistics (star distribution, top keywords)
without needing an AI call.
"""

import re
import math
from collections import Counter
from pathlib import Path

import pandas as pd

# ── Dataset path ──────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "Data" / "reviews_dataset.csv"

# Common English stop-words to exclude from keyword frequency
_STOPWORDS = {
    "the", "a", "an", "is", "it", "its", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "with", "this", "that", "was", "are",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "i", "my", "me",
    "we", "our", "you", "your", "he", "she", "they", "their", "them",
    "so", "very", "just", "also", "if", "as", "by", "from", "am", "no",
    "up", "out", "about", "than", "into", "can", "which", "there", "what",
    "all", "any", "even", "only", "more", "most", "some", "like", "really",
    "good", "bad", "great", "nice", "best", "worst", "one", "two", "three",
    "get", "got", "go", "went", "use", "used", "using", "buy", "bought",
    "product", "price", "overall",
}


# ── Load & filter ─────────────────────────────────────────────────────────────

def load_all_reviews() -> pd.DataFrame:
    """Load the full review CSV and return as a DataFrame."""
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(3).astype(int)
    df["review_text"] = df["review_text"].fillna("").astype(str)
    return df


def get_product_list() -> list[dict]:
    """Return a list of unique products as dicts with id, name, category."""
    df = load_all_reviews()
    products = (
        df[["product_id", "product_name", "category"]]
        .drop_duplicates("product_id")
        .to_dict(orient="records")
    )
    return products


def get_reviews_for_product(product_id: str) -> pd.DataFrame:
    """Filter reviews for a single product."""
    df = load_all_reviews()
    return df[df["product_id"] == product_id].reset_index(drop=True)


def search_products(query: str) -> list[dict]:
    """
    Search products by name or category.
    Returns a list of matching product dicts.
    """
    products = get_product_list()
    query_lower = query.lower()
    return [
        p for p in products
        if query_lower in p["product_name"].lower()
        or query_lower in p["category"].lower()
    ]


# ── Local statistics ──────────────────────────────────────────────────────────

def compute_statistics(df: pd.DataFrame) -> dict:
    """
    Compute local (non-AI) statistics from a product's review DataFrame.

    Returns:
        {
            "total_reviews": int,
            "average_rating": float,
            "star_distribution": {1: int, 2: int, 3: int, 4: int, 5: int},
            "rating_percentage": float,      # 0–100
            "top_keywords": [(word, count)], # top 10
        }
    """
    total = len(df)
    avg = round(df["rating"].mean(), 2) if total > 0 else 0.0

    star_dist = {star: 0 for star in range(1, 6)}
    for star, count in df["rating"].value_counts().items():
        star_dist[int(star)] = int(count)

    rating_pct = round((avg / 5.0) * 100, 1)

    # Build keyword frequency from all review texts
    all_text = " ".join(df["review_text"].tolist()).lower()
    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    filtered = [w for w in words if w not in _STOPWORDS]
    top_keywords = Counter(filtered).most_common(10)

    return {
        "total_reviews": total,
        "average_rating": avg,
        "star_distribution": star_dist,
        "rating_percentage": rating_pct,
        "top_keywords": top_keywords,
    }


def get_review_texts(df: pd.DataFrame) -> list[str]:
    """Return a plain list of review text strings for AI processing."""
    return df["review_text"].tolist()


# ── Sentiment helper (rule-based fallback) ────────────────────────────────────

_POSITIVE_WORDS = {
    "excellent", "amazing", "great", "good", "best", "fantastic", "love",
    "perfect", "outstanding", "superb", "brilliant", "wonderful", "impressed",
    "satisfied", "happy", "smooth", "fast", "comfortable", "durable", "solid",
    "recommend", "recommended", "worth",
}

_NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "horrible", "awful", "worst", "disappoint",
    "disappointed", "disappointing", "slow", "broken", "issue", "problem",
    "complaint", "noise", "noisy", "average", "mediocre", "frustrating",
    "frustrate", "annoying", "useless", "defective",
}


def quick_sentiment_score(text: str) -> str:
    """
    Rule-based sentiment for a single review text.
    Returns 'positive', 'negative', or 'neutral'.
    """
    words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    else:
        return "neutral"


def local_sentiment_breakdown(df: pd.DataFrame) -> dict:
    """
    Compute sentiment breakdown locally (rule-based) as a fallback
    or supplement to AI analysis.
    """
    sentiments = df["review_text"].apply(quick_sentiment_score)
    total = len(sentiments)
    if total == 0:
        return {"positive_percent": 0, "neutral_percent": 0, "negative_percent": 0}
    counts = sentiments.value_counts()
    return {
        "positive_percent": round(counts.get("positive", 0) / total * 100),
        "neutral_percent":  round(counts.get("neutral",  0) / total * 100),
        "negative_percent": round(counts.get("negative", 0) / total * 100),
    }
