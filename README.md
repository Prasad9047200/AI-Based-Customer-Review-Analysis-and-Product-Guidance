# AI-Based Customer Review Analysis and Product Guidance

An AI-powered Streamlit application that analyses customer reviews for any product
and delivers instant insights — sentiment breakdown, pros/cons, keyword analysis,
and a natural-language verdict — all powered by **IBM watsonx.ai (Granite 13B)**.

---

## Features

| Feature | Description |
|---|---|
| 🔍 Product Search | Search products by name or category |
| ⭐ Rating Summary | Average rating + star-distribution bar chart |
| 🤖 AI Sentiment Analysis | IBM watsonx classifies overall sentiment (Positive / Mixed / Negative) |
| 👍 Aspect Extraction | AI lists what customers love and common complaints |
| 📊 Sentiment Breakdown | Positive / Neutral / Negative percentage bars |
| 🏷️ Top Keywords | NLP-derived most-mentioned words |
| 🤖 AI Verdict | Granite 13B writes a concise purchase recommendation |
| 📋 Individual Reviews | Full review cards with local rule-based sentiment tags, sortable |

---

## Project Structure

```
AI-Based Customer Review Analysis and Product Guidance/
│
├── app.py                   # Streamlit UI (main entry-point)
├── ai_analysis.py           # IBM watsonx.ai integration module
├── review_processing.py     # Data loading, filtering, local NLP
├── requirements.txt         # Python dependencies
│
└── Data/
    └── reviews_dataset.csv  # Sample product reviews dataset
```

---

## Architecture

```
User (Browser)
      │
      ▼
 Streamlit UI  (app.py)
      │
      ├──► review_processing.py
      │       • Load CSV dataset
      │       • Filter by product
      │       • Compute stats (rating distribution, keywords)
      │       • Rule-based sentiment fallback
      │
      └──► ai_analysis.py
              • IBM watsonx.ai Credentials
              • ModelInference (Granite 13B)
              • Sentiment analysis   ─┐
              • Aspect extraction    ─┤── Prompt engineering
              • Verdict generation   ─┘
```

---

## Setup & Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the application

```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

### 3. Using the app

1. Type a product name or category (e.g. `Samsung`, `Audio`, `Kitchen`) in the sidebar search box.
2. Select a product from the dropdown.
3. Click **🤖 Analyse Reviews**.
4. Wait a few seconds while IBM watsonx.ai processes the reviews.
5. Explore the sentiment summary, pros/cons, keywords, and AI verdict.

---

## IBM watsonx.ai Configuration

The credentials are already embedded in `ai_analysis.py`:

| Setting | Value |
|---|---|
| API Key | `jhtVJChfbaAV8YVBik-rhJBJb51nw2A3_Ot4xxX7YxVQ` |
| Project ID | `e8836c14-c38a-4df6-8986-91fb920558d8` |
| Region | `us-south` |
| Model | `ibm/granite-13b-instruct-v2` |

> **Note:** To swap credentials, edit the constants at the top of `ai_analysis.py`.

---

## Dataset

The sample dataset (`Data/reviews_dataset.csv`) contains real-style reviews for 3 products:

| Product ID | Product | Category | Reviews |
|---|---|---|---|
| P001 | Samsung Galaxy M54 | Smartphones | 10 |
| P002 | boAt Airdopes 141 | Audio | 8 |
| P003 | Prestige Iris 750W Mixer Grinder | Kitchen Appliances | 7 |

### CSV Schema

```
product_id, product_name, category, reviewer, rating (1-5),
title, review_text, date
```

To add your own products, simply append rows to `Data/reviews_dataset.csv`.

---

## Technologies Used

| Layer | Technology |
|---|---|
| Frontend | Python · Streamlit · Custom CSS |
| AI / LLM | IBM watsonx.ai · Granite 13B Instruct |
| Data | Pandas |
| NLP (local) | Rule-based keyword + sentiment matching |
| Dataset | Custom CSV (extendable) |

---

## Interview Talking Points

- **Prompt Engineering** — three separate structured prompts (sentiment JSON, aspects JSON, free-text verdict) sent to the same Granite model.
- **Graceful Fallback** — if the AI JSON cannot be parsed, local NLP (Counter + stopword filtering) kicks in automatically.
- **Modular Design** — `ai_analysis.py`, `review_processing.py`, and `app.py` are fully decoupled; the backend logic can be ported to a Java/Spring Boot REST API by replacing only `ai_analysis.py`.
- **Extensibility** — swapping the dataset for a live review API (Amazon Product Advertising API, RapidAPI, etc.) requires only changing `review_processing.py`.
