"""
AI-Based Customer Review Analysis and Product Guidance
Streamlit frontend — supports both:
  1. Dataset Mode  — 12 pre-loaded products across 7 categories
  2. Live Fetch    — real-time search on Amazon India + Flipkart
"""

import pandas as pd
import streamlit as st

import review_processing as rp
import ai_analysis as ai
import scraper

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
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f0f4f8; }
[data-testid="stSidebar"]          { background:#1e293b; }
[data-testid="stSidebar"] *        { color:#f8fafc !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input {
    background:#334155; border:1px solid #475569; color:#f8fafc !important;
}
.hero-card {
    background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);
    border-radius:16px; padding:28px 36px; color:white; margin-bottom:20px;
}
.hero-card h1 { font-size:2rem; font-weight:700; margin:0 0 4px 0; }
.hero-card p  { font-size:1rem; opacity:.85; margin:0; }
.metric-card  {
    background:white; border-radius:12px; padding:18px 20px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); text-align:center;
}
.metric-card .value { font-size:1.9rem; font-weight:700; color:#1e3a5f; }
.metric-card .label { font-size:.8rem; color:#64748b; margin-top:4px; }
.section-card {
    background:white; border-radius:12px; padding:22px 26px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:18px;
}
.section-card h3 {
    font-size:1rem; font-weight:600; color:#1e293b;
    margin:0 0 12px 0; border-bottom:2px solid #e2e8f0; padding-bottom:7px;
}
.verdict-box {
    background:linear-gradient(135deg,#f0fdf4,#dcfce7);
    border-left:5px solid #16a34a; border-radius:10px;
    padding:18px 22px; font-size:.97rem; color:#14532d;
    font-style:italic; line-height:1.7;
}
.pill { display:inline-block; padding:5px 13px; border-radius:999px;
        font-size:.8rem; font-weight:600; margin:3px 3px 0 0; }
.pill-green  { background:#d1fae5; color:#065f46; }
.pill-red    { background:#fee2e2; color:#7f1d1d; }
.pill-blue   { background:#dbeafe; color:#1e3a8a; }
.pill-yellow { background:#fef9c3; color:#713f12; }
.badge-recommended    { background:#16a34a; color:#fff; padding:5px 16px;
                        border-radius:999px; font-weight:700; font-size:.88rem; }
.badge-neutral        { background:#d97706; color:#fff; padding:5px 16px;
                        border-radius:999px; font-weight:700; font-size:.88rem; }
.badge-notrecommended { background:#dc2626; color:#fff; padding:5px 16px;
                        border-radius:999px; font-weight:700; font-size:.88rem; }
.star-row { display:flex; align-items:center; gap:8px;
            margin-bottom:5px; font-size:.86rem; }
.bar-bg   { flex:1; background:#e2e8f0; border-radius:4px; height:9px; }
.bar-fill { background:#f59e0b; border-radius:4px; height:9px; }
.star-count { width:28px; text-align:right; color:#475569; }
.review-card {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-radius:10px; padding:14px 18px; margin-bottom:9px;
}
.review-card .reviewer { font-weight:600; color:#1e293b; }
.review-card .rating   { color:#f59e0b; }
.review-card .date     { color:#94a3b8; font-size:.78rem; }
.review-card .body     { margin-top:7px; color:#334155; line-height:1.6; font-size:.92rem; }
.kw-chip {
    display:inline-block; background:#ede9fe; color:#5b21b6;
    padding:4px 11px; border-radius:999px; font-size:.78rem; margin:3px 3px 0 0;
}
.live-badge {
    display:inline-block; background:#ef4444; color:white;
    padding:3px 10px; border-radius:999px; font-size:.75rem;
    font-weight:700; letter-spacing:.5px; margin-left:6px;
}
.source-amz { background:#ff9900; color:#1a1a1a; padding:3px 9px;
              border-radius:999px; font-size:.72rem; font-weight:700; }
.source-flk { background:#2874f0; color:white; padding:3px 9px;
              border-radius:999px; font-size:.72rem; font-weight:700; }
.product-card {
    background:white; border:1px solid #e2e8f0; border-radius:12px;
    padding:14px 16px; cursor:pointer; transition:box-shadow .2s;
}
.product-card:hover { box-shadow:0 4px 12px rgba(0,0,0,.12); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
for k, v in {
    "analysis_result":  None,
    "current_product":  None,
    "current_df":       None,
    "stats":            None,
    "live_products":    [],
    "live_reviews":     [],
    "mode":             "dataset",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Product Search")
    st.markdown("---")

    mode = st.radio(
        "Data Source",
        ["📦 Dataset (12 Products)", "🔴 Live — Amazon & Flipkart"],
        index=0,
    )
    st.session_state.mode = "live" if "Live" in mode else "dataset"

    search_query = st.text_input(
        "Search product",
        placeholder="e.g. Samsung phone, earphones, laptop…",
    )

    # ── DATASET MODE ──────────────────────────────────────────────────────────
    if st.session_state.mode == "dataset":
        all_products = rp.get_product_list()
        matched = rp.search_products(search_query) if search_query else all_products
        if not matched:
            st.warning("No matches found.")
            matched = all_products

        # Group by category for nicer display
        cats = sorted({p["category"] for p in matched})
        cat_filter = st.selectbox("Filter by category", ["All"] + cats)
        if cat_filter != "All":
            matched = [p for p in matched if p["category"] == cat_filter]

        st.markdown(f"**{len(matched)} product(s)**")
        labels = {f"{p['product_name']} ({p['category']})": p for p in matched}
        selected_label = st.selectbox("Select product", list(labels.keys()) if labels else ["—"])
        analyse_btn = st.button("🤖 Analyse Reviews", use_container_width=True, type="primary")

    # ── LIVE MODE ─────────────────────────────────────────────────────────────
    else:
        st.markdown(
            '<span class="live-badge">LIVE</span> Real Amazon products · AI-generated reviews',
            unsafe_allow_html=True,
        )
        rapidapi_key = st.text_input(
            "RapidAPI Key (optional)",
            placeholder="Paste key for real Amazon reviews",
            type="password",
            help="Free key at rapidapi.com → search 'Real-Time Amazon Data'. Leave blank to use AI-generated reviews.",
        )
        st.markdown("")
        fetch_btn = st.button("🔎 Search Products", use_container_width=True, type="primary")

        if fetch_btn and search_query:
            with st.spinner(f"Searching for '{search_query}'…"):
                live_results = scraper.search_all(search_query, max_per_source=6, rapidapi_key=rapidapi_key)
            st.session_state.live_products = live_results
            st.session_state.rapidapi_key = rapidapi_key
            if not live_results:
                st.warning("No products found. Try a different search term.")

        live_products = st.session_state.live_products
        if live_products:
            live_labels = {
                f"{'🟠' if p['product_id'].startswith('AMZ') else '🔵'} {p['product_name'][:55]}": p
                for p in live_products
            }
            selected_live_label = st.selectbox("Select product", list(live_labels.keys()))
            st.markdown(
                f"**Price:** {live_labels[selected_live_label].get('price','N/A')}",
                unsafe_allow_html=True,
            )
            analyse_live_btn = st.button("🤖 Fetch Reviews & Analyse", use_container_width=True, type="primary")
        else:
            analyse_live_btn = False

    st.markdown("---")
    st.markdown(
        "<small style='color:#94a3b8;'>Powered by IBM watsonx.ai · Llama 3.3 70B</small>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Hero banner
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-card">
  <h1>🔍 AI-Based Customer Review Analysis</h1>
  <p>Instant AI-powered insights · Sentiment · Pros &amp; Cons · Smart Verdict &nbsp;|&nbsp;
     <strong>12 dataset products</strong> + <strong>live Amazon &amp; Flipkart</strong></p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Dataset mode — trigger analysis
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.mode == "dataset" and analyse_btn and selected_label != "—":
    selected_product = labels[selected_label]
    df    = rp.get_reviews_for_product(selected_product["product_id"])
    stats = rp.compute_statistics(df)
    reviews = rp.get_review_texts(df)

    with st.spinner("🤖 Analysing with IBM watsonx.ai (Llama 3.3 70B)…"):
        result = ai.run_full_analysis(
            product_name=selected_product["product_name"],
            reviews=reviews,
            avg_rating=stats["average_rating"],
        )

    if not result.get("sentiment_breakdown") or not any(result["sentiment_breakdown"].values()):
        result["sentiment_breakdown"] = rp.local_sentiment_breakdown(df)

    st.session_state.update({
        "analysis_result": result,
        "current_product": selected_product,
        "current_df":      df,
        "stats":           stats,
    })

    if result.get("source") == "watsonx":
        st.success("✅ Analysis powered by IBM watsonx.ai · Llama 3.3 70B", icon="🤖")
    else:
        st.info("ℹ️ Results from local NLP engine (AI API unavailable).", icon="🔍")

# ─────────────────────────────────────────────────────────────────────────────
# Live mode — fetch + analyse
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.mode == "live" and "analyse_live_btn" in dir() and analyse_live_btn and live_products:
    selected_product = live_labels[selected_live_label]
    rapi_key = st.session_state.get("rapidapi_key", "")

    with st.spinner(f"🤖 Generating AI reviews for {selected_product['product_name']}…"):
        live_reviews = scraper.fetch_reviews(selected_product, max_reviews=15, rapidapi_key=rapi_key)

    # fetch_reviews always returns something (AI fallback) — no error possible
    review_source = "Amazon API" if any(
        r.get("reviewer","") not in ["Rahul Sharma","Priya Verma","Amit Kumar"]
        for r in live_reviews[:3]
    ) else "AI-Generated"

    df = pd.DataFrame(live_reviews)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(3).astype(int)
    df["date"]   = pd.to_datetime(df["date"], errors="coerce")

    stats   = rp.compute_statistics(df)
    reviews = rp.get_review_texts(df)

    with st.spinner(f"🤖 Analysing {len(reviews)} reviews with IBM watsonx.ai…"):
        result = ai.run_full_analysis(
            product_name=selected_product["product_name"],
            reviews=reviews,
            avg_rating=stats["average_rating"],
        )

    if not result.get("sentiment_breakdown") or not any(result["sentiment_breakdown"].values()):
        result["sentiment_breakdown"] = rp.local_sentiment_breakdown(df)

    st.session_state.update({
        "analysis_result": result,
        "current_product": selected_product,
        "current_df":      df,
        "stats":           stats,
    })

    src_label = f"🟠 Amazon" if selected_product["product_id"].startswith("AMZ") else "🔵 Flipkart"
    rev_label = f"{len(reviews)} reviews ({review_source})"
    if result.get("source") == "watsonx":
        st.success(f"✅ {rev_label} analysed via IBM watsonx.ai · {src_label}", icon="🤖")
    else:
        st.info(f"ℹ️ {rev_label} analysed with local NLP · {src_label}", icon="🔍")

# ─────────────────────────────────────────────────────────────────────────────
# Render results
# ─────────────────────────────────────────────────────────────────────────────
result  = st.session_state.analysis_result
product = st.session_state.current_product
df      = st.session_state.current_df
stats   = st.session_state.stats

if result is None:
    # ── Landing page when nothing is selected yet ─────────────────────────────
    st.markdown("""
    <div class="section-card" style="text-align:center; padding:44px;">
        <div style="font-size:3rem;">🛒</div>
        <h2 style="color:#1e3a5f; margin:12px 0 8px 0;">Get started</h2>
        <p style="color:#64748b; max-width:460px; margin:0 auto;">
            <strong>Dataset mode:</strong> Pick from 12 pre-loaded Indian products across 7 categories.<br><br>
            <strong>Live mode:</strong> Search Amazon India &amp; Flipkart in real-time — type any product
            name, click <em>Search Live Products</em>, then <em>Fetch Reviews &amp; Analyse</em>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Show all dataset products as cards
    st.markdown("### 📦 Available Dataset Products")
    all_prods = rp.get_product_list()
    cats = sorted({p["category"] for p in all_prods})
    for cat in cats:
        st.markdown(f"**{cat}**")
        cols = st.columns(4)
        for i, p in enumerate([x for x in all_prods if x["category"] == cat]):
            with cols[i % 4]:
                st.markdown(
                    f"""<div class="product-card">
                        <div style="font-size:.85rem;font-weight:600;color:#1e293b;">{p['product_name']}</div>
                        <div style="font-size:.75rem;color:#64748b;margin-top:3px;">{p['category']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        st.markdown("")
    st.stop()

# ── Summary bar ───────────────────────────────────────────────────────────────
rec       = result.get("recommendation", "Neutral")
badge_cls = {"Recommended": "badge-recommended", "Not Recommended": "badge-notrecommended"}.get(rec, "badge-neutral")
sentiment = result.get("overall_sentiment", "Mixed")
s_emoji   = {"Mostly Positive": "😊", "Mixed": "😐", "Mostly Negative": "😞"}.get(sentiment, "😐")

# Source/platform badge
pid = product.get("product_id", "")
if pid.startswith("AMZ_"):
    platform_html = '<span class="source-amz">🟠 Amazon</span>'
elif pid.startswith("FLK_"):
    platform_html = '<span class="source-flk">🔵 Flipkart</span>'
else:
    platform_html = '<span style="background:#e2e8f0;color:#475569;padding:3px 9px;border-radius:999px;font-size:.72rem;font-weight:700;">📦 Dataset</span>'

st.markdown(f"""
<div class="section-card" style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
    <div>
        <div style="font-size:.75rem;color:#64748b;margin-bottom:3px;">PRODUCT {platform_html}</div>
        <div style="font-size:1.25rem;font-weight:700;color:#1e293b;">{product['product_name']}</div>
        <div style="color:#64748b;font-size:.85rem;">{product['category']}</div>
    </div>
    <div>
        <div style="font-size:.75rem;color:#64748b;margin-bottom:3px;">OVERALL OPINION</div>
        <span class="{badge_cls}">{rec}</span>
    </div>
    <div>
        <div style="font-size:.75rem;color:#64748b;margin-bottom:3px;">CUSTOMER SENTIMENT</div>
        <div style="font-size:1rem;font-weight:600;">{s_emoji} {sentiment}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Metrics row ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
sb      = result.get("sentiment_breakdown", {})
pos_pct = sb.get("positive_percent", 0)
neg_pct = sb.get("negative_percent", 0)
stars   = "⭐" * round(stats["average_rating"])

with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="value">{stats['average_rating']}</div>
        <div class="label">Avg Rating<br>{stars}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="value">{stats['total_reviews']}</div>
        <div class="label">Total Reviews</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="value" style="color:#16a34a;">{pos_pct}%</div>
        <div class="label">Positive</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="value" style="color:#dc2626;">{neg_pct}%</div>
        <div class="label">Negative</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main content columns ──────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    # Pros
    likes      = result.get("what_customers_like", [])
    likes_html = "".join(f'<span class="pill pill-green">✔ {i}</span>' for i in likes) or "<em style='color:#94a3b8;'>—</em>"
    st.markdown(f"""<div class="section-card"><h3>👍 What Customers Like</h3>{likes_html}</div>""", unsafe_allow_html=True)

    # Cons
    complaints  = result.get("common_complaints", [])
    comps_html  = "".join(f'<span class="pill pill-red">✖ {i}</span>' for i in complaints) or "<em style='color:#94a3b8;'>—</em>"
    st.markdown(f"""<div class="section-card"><h3>👎 Common Complaints</h3>{comps_html}</div>""", unsafe_allow_html=True)

    # Features
    features   = result.get("key_features_mentioned", [])
    feat_html  = "".join(f'<span class="pill pill-blue">🔹 {i}</span>' for i in features) or "<em style='color:#94a3b8;'>—</em>"
    st.markdown(f"""<div class="section-card"><h3>🔑 Key Features Mentioned</h3>{feat_html}</div>""", unsafe_allow_html=True)

with col_right:
    # Star distribution
    star_rows = ""
    total_rev = stats["total_reviews"] or 1
    for star in range(5, 0, -1):
        cnt = stats["star_distribution"].get(star, 0)
        pct = cnt / total_rev * 100
        star_rows += f"""<div class="star-row">
            <span>{"⭐"*star}</span>
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
            <span class="star-count">{cnt}</span></div>"""
    st.markdown(f"""<div class="section-card"><h3>⭐ Rating Distribution</h3>{star_rows}</div>""", unsafe_allow_html=True)

    # Sentiment bars
    neu_pct = sb.get("neutral_percent", 0)
    st.markdown(f"""<div class="section-card"><h3>📊 Sentiment Breakdown</h3>
        <div style="display:flex;flex-direction:column;gap:8px;">
            <div>
                <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:2px;">
                    <span>😊 Positive</span><span>{pos_pct}%</span></div>
                <div class="bar-bg"><div style="background:#16a34a;height:9px;border-radius:4px;width:{pos_pct}%"></div></div>
            </div>
            <div>
                <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:2px;">
                    <span>😐 Neutral</span><span>{neu_pct}%</span></div>
                <div class="bar-bg"><div style="background:#d97706;height:9px;border-radius:4px;width:{neu_pct}%"></div></div>
            </div>
            <div>
                <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:2px;">
                    <span>😞 Negative</span><span>{neg_pct}%</span></div>
                <div class="bar-bg"><div style="background:#dc2626;height:9px;border-radius:4px;width:{neg_pct}%"></div></div>
            </div>
        </div></div>""", unsafe_allow_html=True)

    # Top keywords
    kw = "".join(f'<span class="kw-chip">{w} ({c})</span>' for w, c in stats.get("top_keywords", []))
    st.markdown(f"""<div class="section-card"><h3>🏷️ Top Keywords</h3>
        {kw or "<em style='color:#94a3b8;'>—</em>"}</div>""", unsafe_allow_html=True)

# ── AI Verdict ────────────────────────────────────────────────────────────────
verdict = result.get("verdict", "")
if verdict:
    st.markdown(f"""<div class="section-card"><h3>🤖 AI Verdict</h3>
        <div class="verdict-box">"{verdict}"</div></div>""", unsafe_allow_html=True)

# ── Individual reviews ────────────────────────────────────────────────────────
with st.expander(f"📋 View All {stats['total_reviews']} Customer Reviews", expanded=False):
    sort_by   = st.selectbox("Sort by", ["Newest First", "Highest Rating", "Lowest Rating"], key="sort_rev")
    sorted_df = df.sort_values(
        "date" if sort_by == "Newest First" else "rating",
        ascending=(sort_by == "Lowest Rating"),
    )
    for _, row in sorted_df.iterrows():
        stars_str   = "⭐" * int(row["rating"])
        date_val    = row["date"]
        date_str    = pd.to_datetime(date_val).strftime("%d %b %Y") if pd.notna(date_val) else "—"
        sent_tag    = rp.quick_sentiment_score(row["review_text"])
        tag_cls     = {"positive": "pill-green", "negative": "pill-red"}.get(sent_tag, "pill-yellow")
        st.markdown(f"""<div class="review-card">
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:5px;">
                <span class="reviewer">🧑 {row['reviewer']}</span>
                <span>
                    <span class="rating">{stars_str}</span>
                    <span class="pill {tag_cls}" style="font-size:.72rem;">{sent_tag.capitalize()}</span>
                </span>
            </div>
            <div class="date">{date_str}</div>
            <div class="body">{row['review_text']}</div>
        </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="border:none;border-top:1px solid #e2e8f0;margin:28px 0 10px 0;">
<div style="text-align:center;color:#94a3b8;font-size:.76rem;">
    AI-Based Customer Review Analysis and Product Guidance &nbsp;·&nbsp;
    IBM watsonx.ai (Llama 3.3 70B) &nbsp;·&nbsp; Amazon India &amp; Flipkart Live Data
</div>
""", unsafe_allow_html=True)
