"""
AI-Based Customer Review Analysis and Product Guidance
Streamlit frontend — single-file app that wires together
review_processing.py  +  ai_analysis.py
"""

import time
import streamlit as st
import pandas as pd

import review_processing as rp
import ai_analysis as ai

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Review Analyser",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ---------- global ---------- */
    [data-testid="stAppViewContainer"] {
        background: #f0f4f8;
    }
    [data-testid="stSidebar"] {
        background: #1e293b;
        color: #f8fafc;
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background: #334155;
        border: 1px solid #475569;
        color: #f8fafc !important;
    }

    /* ---------- hero card ---------- */
    .hero-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
        border-radius: 16px;
        padding: 32px 40px;
        color: white;
        margin-bottom: 24px;
    }
    .hero-card h1 { font-size: 2.2rem; font-weight: 700; margin: 0 0 6px 0; }
    .hero-card p  { font-size: 1.05rem; opacity: .85; margin: 0; }

    /* ---------- metric cards ---------- */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 4px rgba(0,0,0,.08);
        text-align: center;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #1e3a5f; }
    .metric-card .label { font-size: .82rem; color: #64748b; margin-top: 4px; }

    /* ---------- section card ---------- */
    .section-card {
        background: white;
        border-radius: 12px;
        padding: 24px 28px;
        box-shadow: 0 1px 4px rgba(0,0,0,.08);
        margin-bottom: 20px;
    }
    .section-card h3 {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 14px 0;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
    }

    /* ---------- verdict box ---------- */
    .verdict-box {
        background: linear-gradient(135deg, #f0fdf4, #dcfce7);
        border-left: 5px solid #16a34a;
        border-radius: 10px;
        padding: 20px 24px;
        font-size: 1rem;
        color: #14532d;
        font-style: italic;
        line-height: 1.7;
    }

    /* ---------- pill ---------- */
    .pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 999px;
        font-size: .82rem;
        font-weight: 600;
        margin: 4px 4px 0 0;
    }
    .pill-green  { background: #d1fae5; color: #065f46; }
    .pill-red    { background: #fee2e2; color: #7f1d1d; }
    .pill-blue   { background: #dbeafe; color: #1e3a8a; }
    .pill-yellow { background: #fef9c3; color: #713f12; }

    /* ---------- recommendation badge ---------- */
    .badge-recommended    { background:#16a34a; color:#fff; padding:6px 18px;
                            border-radius:999px; font-weight:700; font-size:.92rem; }
    .badge-neutral        { background:#d97706; color:#fff; padding:6px 18px;
                            border-radius:999px; font-weight:700; font-size:.92rem; }
    .badge-notrecommended { background:#dc2626; color:#fff; padding:6px 18px;
                            border-radius:999px; font-weight:700; font-size:.92rem; }

    /* ---------- star bar ---------- */
    .star-row {
        display: flex; align-items: center; gap: 8px;
        margin-bottom: 6px; font-size: .88rem;
    }
    .bar-bg { flex: 1; background: #e2e8f0; border-radius: 4px; height: 10px; }
    .bar-fill { background: #f59e0b; border-radius: 4px; height: 10px; }
    .star-count { width: 30px; text-align: right; color: #475569; }

    /* ---------- review card ---------- */
    .review-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .review-card .reviewer { font-weight: 600; color: #1e293b; }
    .review-card .rating   { color: #f59e0b; }
    .review-card .date     { color: #94a3b8; font-size: .8rem; }
    .review-card .body     { margin-top: 8px; color: #334155; line-height: 1.6; }

    /* ---------- keyword chip ---------- */
    .kw-chip {
        display: inline-block;
        background: #ede9fe;
        color: #5b21b6;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: .8rem;
        margin: 3px 3px 0 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────
for key, default in {
    "analysis_result": None,
    "current_product": None,
    "current_df": None,
    "stats": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — product search
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Product Search")
    st.markdown("---")

    search_query = st.text_input(
        "Search by product name or category",
        placeholder="e.g. Samsung, Audio, Kitchen…",
    )

    all_products = rp.get_product_list()

    if search_query:
        matched = rp.search_products(search_query)
        if not matched:
            st.warning("No products found. Try a different keyword.")
            matched = []
    else:
        matched = all_products

    st.markdown(f"**{len(matched)} product(s) found**")

    # Build label → product dict
    product_labels = {
        f"{p['product_name']} ({p['category']})": p for p in matched
    }

    selected_label = st.selectbox(
        "Select a product",
        options=list(product_labels.keys()) if product_labels else ["—"],
        index=0,
    )

    analyse_btn = st.button("🤖 Analyse Reviews", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown(
        "<small style='color:#94a3b8;'>Powered by IBM watsonx.ai · "
        "IBM Granite 13B</small>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Hero banner
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-card">
      <h1>🔍 AI-Based Customer Review Analysis</h1>
      <p>Instant AI-powered insights from customer reviews — sentiment, pros/cons, and a smart verdict.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Trigger analysis
# ─────────────────────────────────────────────────────────────────────────────
if analyse_btn and selected_label and selected_label != "—":
    selected_product = product_labels[selected_label]
    df = rp.get_reviews_for_product(selected_product["product_id"])
    stats = rp.compute_statistics(df)
    reviews = rp.get_review_texts(df)

    with st.spinner("🤖 Analysing reviews with IBM watsonx.ai (Llama 3.3 70B)…"):
        result = ai.run_full_analysis(
            product_name=selected_product["product_name"],
            reviews=reviews,
            avg_rating=stats["average_rating"],
        )

    # If AI sentiment_breakdown is missing/failed, fall back to local
    if not result.get("sentiment_breakdown") or not any(result["sentiment_breakdown"].values()):
        result["sentiment_breakdown"] = rp.local_sentiment_breakdown(df)

    st.session_state.analysis_result = result
    st.session_state.current_product = selected_product
    st.session_state.current_df = df
    st.session_state.stats = stats

    if result.get("source") == "watsonx":
        st.success("✅ Analysis powered by IBM watsonx.ai · Llama 3.3 70B", icon="🤖")
    else:
        st.info("ℹ️ Results generated by local NLP engine (AI API unavailable).", icon="🔍")

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────
result   = st.session_state.analysis_result
product  = st.session_state.current_product
df       = st.session_state.current_df
stats    = st.session_state.stats

if result is None:
    # Landing placeholder
    st.markdown(
        """
        <div class="section-card" style="text-align:center; padding: 48px;">
            <div style="font-size:3rem;">🛒</div>
            <h2 style="color:#1e3a5f; margin: 12px 0 8px 0;">Get started</h2>
            <p style="color:#64748b;">
                Search for a product in the sidebar and click <strong>Analyse Reviews</strong>
                to get an AI-powered breakdown.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Top summary bar ───────────────────────────────────────────────────────────
rec = result.get("recommendation", "Neutral")
badge_cls = {
    "Recommended":     "badge-recommended",
    "Not Recommended": "badge-notrecommended",
}.get(rec, "badge-neutral")

overall_sentiment = result.get("overall_sentiment", "Mixed")
sentiment_emoji = {
    "Mostly Positive": "😊",
    "Mixed":           "😐",
    "Mostly Negative": "😞",
}.get(overall_sentiment, "😐")

st.markdown(
    f"""
    <div class="section-card" style="display:flex; align-items:center; gap:32px; flex-wrap:wrap;">
        <div>
            <div style="font-size:.8rem;color:#64748b;margin-bottom:4px;">PRODUCT</div>
            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{product['product_name']}</div>
            <div style="color:#64748b;font-size:.88rem;">{product['category']}</div>
        </div>
        <div>
            <div style="font-size:.8rem;color:#64748b;margin-bottom:4px;">OVERALL OPINION</div>
            <span class="{badge_cls}">{rec}</span>
        </div>
        <div>
            <div style="font-size:.8rem;color:#64748b;margin-bottom:4px;">CUSTOMER SENTIMENT</div>
            <div style="font-size:1.05rem;font-weight:600;">
                {sentiment_emoji} {overall_sentiment}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Key metrics row ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

stars_html = "⭐" * round(stats["average_rating"])

with c1:
    st.markdown(
        f"""<div class="metric-card">
            <div class="value">{stats['average_rating']}</div>
            <div class="label">Average Rating<br>{stars_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class="metric-card">
            <div class="value">{stats['total_reviews']}</div>
            <div class="label">Total Reviews</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c3:
    sb = result.get("sentiment_breakdown", {})
    pos_pct = sb.get("positive_percent", 0)
    st.markdown(
        f"""<div class="metric-card">
            <div class="value" style="color:#16a34a;">{pos_pct}%</div>
            <div class="label">Positive Sentiment</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c4:
    neg_pct = sb.get("negative_percent", 0)
    st.markdown(
        f"""<div class="metric-card">
            <div class="value" style="color:#dc2626;">{neg_pct}%</div>
            <div class="label">Negative Sentiment</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Pros / Cons / Features + Star distribution ────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    # Pros
    likes = result.get("what_customers_like", [])
    likes_html = "".join(
        f'<span class="pill pill-green">✔ {item}</span>' for item in likes
    ) if likes else "<em style='color:#94a3b8;'>No data</em>"
    st.markdown(
        f"""<div class="section-card">
            <h3>👍 What Customers Like</h3>
            {likes_html}
        </div>""",
        unsafe_allow_html=True,
    )

    # Cons
    complaints = result.get("common_complaints", [])
    comps_html = "".join(
        f'<span class="pill pill-red">✖ {item}</span>' for item in complaints
    ) if complaints else "<em style='color:#94a3b8;'>No data</em>"
    st.markdown(
        f"""<div class="section-card">
            <h3>👎 Common Complaints</h3>
            {comps_html}
        </div>""",
        unsafe_allow_html=True,
    )

    # Key features
    features = result.get("key_features_mentioned", [])
    feat_html = "".join(
        f'<span class="pill pill-blue">🔹 {item}</span>' for item in features
    ) if features else "<em style='color:#94a3b8;'>No data</em>"
    st.markdown(
        f"""<div class="section-card">
            <h3>🔑 Key Features Mentioned</h3>
            {feat_html}
        </div>""",
        unsafe_allow_html=True,
    )

with col_right:
    # Star distribution
    star_rows = ""
    total_rev = stats["total_reviews"] or 1
    for star in range(5, 0, -1):
        count = stats["star_distribution"].get(star, 0)
        pct = count / total_rev * 100
        star_rows += f"""
        <div class="star-row">
            <span>{"⭐" * star}</span>
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
            <span class="star-count">{count}</span>
        </div>"""

    st.markdown(
        f"""<div class="section-card">
            <h3>⭐ Rating Distribution</h3>
            {star_rows}
        </div>""",
        unsafe_allow_html=True,
    )

    # Sentiment donut (rendered as inline bar chart via HTML)
    sb = result.get("sentiment_breakdown", {})
    pos = sb.get("positive_percent", 0)
    neu = sb.get("neutral_percent",  0)
    neg = sb.get("negative_percent", 0)
    st.markdown(
        f"""<div class="section-card">
            <h3>📊 Sentiment Breakdown</h3>
            <div style="display:flex;flex-direction:column;gap:8px;">
                <div>
                    <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:2px;">
                        <span>😊 Positive</span><span>{pos}%</span>
                    </div>
                    <div class="bar-bg">
                        <div style="background:#16a34a;height:10px;border-radius:4px;width:{pos}%"></div>
                    </div>
                </div>
                <div>
                    <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:2px;">
                        <span>😐 Neutral</span><span>{neu}%</span>
                    </div>
                    <div class="bar-bg">
                        <div style="background:#d97706;height:10px;border-radius:4px;width:{neu}%"></div>
                    </div>
                </div>
                <div>
                    <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:2px;">
                        <span>😞 Negative</span><span>{neg}%</span>
                    </div>
                    <div class="bar-bg">
                        <div style="background:#dc2626;height:10px;border-radius:4px;width:{neg}%"></div>
                    </div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Top keywords
    kw_chips = "".join(
        f'<span class="kw-chip">{word} ({cnt})</span>'
        for word, cnt in stats.get("top_keywords", [])
    )
    st.markdown(
        f"""<div class="section-card">
            <h3>🏷️ Top Keywords</h3>
            {kw_chips if kw_chips else "<em style='color:#94a3b8;'>—</em>"}
        </div>""",
        unsafe_allow_html=True,
    )

# ── AI Verdict ────────────────────────────────────────────────────────────────
verdict = result.get("verdict", "")
if verdict:
    st.markdown(
        f"""<div class="section-card">
            <h3>🤖 AI Verdict</h3>
            <div class="verdict-box">"{verdict}"</div>
        </div>""",
        unsafe_allow_html=True,
    )

# ── Individual reviews ────────────────────────────────────────────────────────
with st.expander(f"📋 View All {stats['total_reviews']} Customer Reviews", expanded=False):
    sort_by = st.selectbox("Sort by", ["Newest First", "Highest Rating", "Lowest Rating"], key="sort_reviews")
    sorted_df = df.copy()
    if sort_by == "Newest First":
        sorted_df = sorted_df.sort_values("date", ascending=False)
    elif sort_by == "Highest Rating":
        sorted_df = sorted_df.sort_values("rating", ascending=False)
    else:
        sorted_df = sorted_df.sort_values("rating", ascending=True)

    for _, row in sorted_df.iterrows():
        stars = "⭐" * int(row["rating"])
        date_str = pd.to_datetime(row["date"]).strftime("%d %b %Y")
        sentiment_tag = rp.quick_sentiment_score(row["review_text"])
        tag_cls = {"positive": "pill-green", "negative": "pill-red"}.get(sentiment_tag, "pill-yellow")
        st.markdown(
            f"""<div class="review-card">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">
                    <span class="reviewer">🧑 {row['reviewer']}</span>
                    <span>
                        <span class="rating">{stars}</span>
                        <span class="pill {tag_cls}" style="font-size:.75rem;">{sentiment_tag.capitalize()}</span>
                    </span>
                </div>
                <div class="date">{date_str}</div>
                <div class="body">{row['review_text']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:32px 0 12px 0;">
    <div style="text-align:center;color:#94a3b8;font-size:.78rem;">
        AI-Based Customer Review Analysis and Product Guidance &nbsp;·&nbsp;
        Powered by IBM watsonx.ai (Granite 13B)
    </div>
    """,
    unsafe_allow_html=True,
)
