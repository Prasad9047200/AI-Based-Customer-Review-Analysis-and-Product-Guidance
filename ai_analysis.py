"""
AI Analysis Module
Uses IBM watsonx.ai (ibm-watsonx-ai SDK) to perform:
  - Sentiment analysis
  - Aspect extraction (pros / cons)
  - AI-generated summary & verdict

Falls back to local rule-based analysis if the API call fails.
"""

import json
import re
from collections import Counter
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# ── Credentials ──────────────────────────────────────────────────────────────
IBM_API_KEY   = "jhtVJChfbaAV8YVBik-rhJBJb51nw2A3_Ot4xxX7YxVQ"
IBM_PROJECT_ID = "e8836c14-c38a-4df6-8986-91fb920558d8"
IBM_URL       = "https://us-south.ml.cloud.ibm.com"

# ── Model — pick the first supported instruct model ──────────────────────────
# Confirmed supported by this project's watsonx environment:
MODEL_ID = "meta-llama/llama-3-3-70b-instruct"


def _get_model() -> ModelInference:
    """Initialise and return a watsonx ModelInference object."""
    credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
    return ModelInference(
        model_id=MODEL_ID,
        credentials=credentials,
        project_id=IBM_PROJECT_ID,
        params={
            "max_new_tokens": 600,
            "temperature": 0.2,
            "decoding_method": "greedy",
        },
    )


def _call_model(prompt: str) -> str:
    """Send a prompt to watsonx and return the generated text."""
    model = _get_model()
    response = model.generate_text(prompt=prompt)
    return response.strip() if isinstance(response, str) else str(response).strip()


# ── Prompts ───────────────────────────────────────────────────────────────────

def _build_sentiment_prompt(product_name: str, reviews_text: str) -> str:
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a product review analyst. Respond ONLY with a valid JSON object, no explanation.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Analyze the sentiment of these customer reviews for "{product_name}".

Reviews:
{reviews_text}

Respond with ONLY this JSON:
{{
  "overall_sentiment": "Mostly Positive",
  "recommendation": "Recommended",
  "sentiment_breakdown": {{
    "positive_percent": 70,
    "neutral_percent": 20,
    "negative_percent": 10
  }}
}}
Replace the numbers and labels with your actual analysis.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


def _build_aspects_prompt(product_name: str, reviews_text: str) -> str:
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a product review analyst. Respond ONLY with a valid JSON object, no explanation.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Extract key aspects from customer reviews for "{product_name}".

Reviews:
{reviews_text}

Respond with ONLY this JSON:
{{
  "what_customers_like": ["aspect 1", "aspect 2", "aspect 3"],
  "common_complaints": ["complaint 1", "complaint 2"],
  "key_features_mentioned": ["feature 1", "feature 2", "feature 3"]
}}
Replace with actual aspects from the reviews.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


def _build_verdict_prompt(product_name: str, reviews_text: str, avg_rating: float) -> str:
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert product reviewer. Write a concise 2-3 sentence verdict.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Write a purchase verdict for "{product_name}" (average rating: {avg_rating:.1f}/5) based on these reviews:

{reviews_text}

Your verdict must:
1. Highlight the main strengths
2. Mention key weaknesses
3. Say who this product is best suited for

Write ONLY the verdict text, no labels:
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


# ── JSON parsing helper ───────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Robustly extract a JSON object from model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ── Local fallback analysis (no API needed) ───────────────────────────────────

_POS_WORDS = {
    "excellent", "amazing", "great", "good", "best", "fantastic", "love",
    "perfect", "outstanding", "superb", "wonderful", "impressed", "satisfied",
    "happy", "smooth", "fast", "comfortable", "durable", "solid", "recommend",
    "recommended", "worth", "impressive", "powerful", "clear", "crisp",
}
_NEG_WORDS = {
    "bad", "poor", "terrible", "horrible", "awful", "worst", "disappoint",
    "disappointed", "disappointing", "slow", "broken", "issue", "problem",
    "noisy", "average", "mediocre", "frustrating", "useless", "defective",
    "stopped", "noise", "vibrate", "vibrates",
}
_STOPWORDS = {
    "the","a","an","is","it","its","in","on","at","to","for","of","and","or",
    "but","not","with","this","that","was","are","be","been","have","has","had",
    "do","does","did","will","would","could","should","i","my","me","we","you",
    "your","he","she","they","their","so","very","just","also","if","as","by",
    "from","am","no","up","out","about","than","into","can","which","there",
    "all","any","even","only","more","most","some","like","really","good","bad",
    "great","nice","best","worst","one","two","three","get","got","go","use",
    "used","using","buy","bought","product","price","overall","also","very",
}


def _local_fallback(product_name: str, reviews: list[str], avg_rating: float) -> dict:
    """Generate a complete analysis result using only local logic."""
    sentiments = []
    for rev in reviews:
        words = set(re.findall(r'\b[a-z]{3,}\b', rev.lower()))
        pos = len(words & _POS_WORDS)
        neg = len(words & _NEG_WORDS)
        sentiments.append("positive" if pos > neg else ("negative" if neg > pos else "neutral"))

    total = len(sentiments) or 1
    pos_pct = round(sentiments.count("positive") / total * 100)
    neu_pct = round(sentiments.count("neutral")  / total * 100)
    neg_pct = round(sentiments.count("negative") / total * 100)

    if pos_pct >= 60:
        overall = "Mostly Positive"
        rec = "Recommended"
    elif neg_pct >= 50:
        overall = "Mostly Negative"
        rec = "Not Recommended"
    else:
        overall = "Mixed"
        rec = "Neutral"

    # Extract top positive and negative words as aspect proxies
    all_words = re.findall(r'\b[a-z]{4,}\b', " ".join(reviews).lower())
    filtered = [w for w in all_words if w not in _STOPWORDS]
    freq = Counter(filtered).most_common(30)
    top_words = [w for w, _ in freq]

    pos_aspects = [w.capitalize() for w in top_words if w in _POS_WORDS][:4]
    neg_aspects = [w.capitalize() for w in top_words if w in _NEG_WORDS][:3]
    features    = [w.capitalize() for w in top_words
                   if w not in _POS_WORDS and w not in _NEG_WORDS][:4]

    verdict = (
        f"Based on {total} customer reviews, {product_name} has an average rating of "
        f"{avg_rating:.1f}/5. Customers primarily highlight "
        f"{', '.join(pos_aspects[:2]) if pos_aspects else 'overall performance'} as strengths"
        f"{', while common concerns include ' + ', '.join(neg_aspects[:2]) if neg_aspects else ''}. "
        f"This product is best suited for users who prioritize "
        f"{pos_aspects[0].lower() if pos_aspects else 'value for money'}."
    )

    return {
        "overall_sentiment": overall,
        "recommendation": rec,
        "sentiment_breakdown": {
            "positive_percent": pos_pct,
            "neutral_percent":  neu_pct,
            "negative_percent": neg_pct,
        },
        "what_customers_like": pos_aspects or ["Good overall quality"],
        "common_complaints":   neg_aspects or ["Minor issues reported"],
        "key_features_mentioned": features or ["Performance", "Build quality", "Value"],
        "verdict": verdict,
        "source": "local",
    }


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_sentiment(product_name: str, reviews: list[str]) -> dict:
    reviews_text = "\n".join(f"- {r}" for r in reviews[:15])
    prompt = _build_sentiment_prompt(product_name, reviews_text)
    try:
        raw = _call_model(prompt)
        result = _extract_json(raw)
        return {
            "overall_sentiment": result.get("overall_sentiment", "Mixed"),
            "recommendation":    result.get("recommendation", "Neutral"),
            "sentiment_breakdown": result.get("sentiment_breakdown", {
                "positive_percent": 50, "neutral_percent": 25, "negative_percent": 25,
            }),
        }
    except Exception:
        return {}


def extract_aspects(product_name: str, reviews: list[str]) -> dict:
    reviews_text = "\n".join(f"- {r}" for r in reviews[:15])
    prompt = _build_aspects_prompt(product_name, reviews_text)
    try:
        raw = _call_model(prompt)
        result = _extract_json(raw)
        return {
            "what_customers_like":    result.get("what_customers_like", []),
            "common_complaints":      result.get("common_complaints", []),
            "key_features_mentioned": result.get("key_features_mentioned", []),
        }
    except Exception:
        return {}


def generate_verdict(product_name: str, reviews: list[str], avg_rating: float) -> str:
    reviews_text = "\n".join(f"- {r}" for r in reviews[:15])
    prompt = _build_verdict_prompt(product_name, reviews_text, avg_rating)
    try:
        return _call_model(prompt)
    except Exception:
        return ""


def run_full_analysis(product_name: str, reviews: list[str], avg_rating: float) -> dict:
    """
    Runs full AI analysis via IBM watsonx.
    If ANY step fails, falls back entirely to local analysis.
    Returns a unified result dict.
    """
    try:
        sentiment = analyze_sentiment(product_name, reviews)
        aspects   = extract_aspects(product_name, reviews)
        verdict   = generate_verdict(product_name, reviews, avg_rating)

        # If the API returned empty/incomplete results, use local fallback
        if not sentiment or not aspects.get("what_customers_like"):
            raise ValueError("Incomplete AI response — using local fallback")

        return {
            **sentiment,
            **aspects,
            "verdict": verdict,
            "source": "watsonx",
        }

    except Exception:
        # Full local fallback — app never crashes
        return _local_fallback(product_name, reviews, avg_rating)
