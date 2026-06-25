# NewsPulse AI 🔍

**An AI-powered tech and AI news intelligence assistant** that aggregates content from multiple sources, analyzes sentiment and trends, and provides a grounded, citation-backed conversational interface for exploring the latest developments in AI and technology.

🌐 **Live Demo**: [news-pulse-ai-rosy.vercel.app](https://news-pulse-ai-rosy.vercel.app)
⚙️ **Backend API**: [newspulseai-lvyy.onrender.com](https://newspulseai-lvyy.onrender.com/docs)

---

## 📌 Overview

NewsPulse AI is a full-stack portfolio project that combines a multi-source news ingestion pipeline with an agentic RAG (Retrieval-Augmented Generation) chatbot. Users can browse curated AI/tech headlines, read articles alongside community discussions, ask questions grounded in recent news, and explore sentiment trends — all from a single interface.

### What makes it different from a generic news aggregator:

- **Cross-source synthesis** — formal news articles (NewsAPI.ai, newsdata.io) are enriched with community discussion from Hacker News and DEV.to, enabling the chatbot to answer both "what happened?" and "what's the community saying about it?"
- **Agentic routing** — a LangGraph-based agent classifies each user query and routes it to the appropriate flow: Q&A retrieval, daily digest, or trend analysis
- **Source-grounded answers** — every chatbot response cites the articles it used, with clickable citation cards linking back to the original source
- **Automated ingestion** — a scheduled pipeline continuously ingests, deduplicates, classifies, and embeds new articles without manual intervention

---

## 🧱 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                      │
│  NewsAPI.ai │ newsdata.io │ Hacker News │ DEV.to │ Tavily  │
└──────────────────────────┬──────────────────────────────────┘
                           │ normalize → deduplicate
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                           │
│  Classify (category) → Summarize → Sentiment → Embed        │
│  Write to PostgreSQL (Supabase) + ChromaDB (vectors)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              AGENTIC RAG LAYER  (LangGraph)                  │
│                                                              │
│  Router Node → qa    → Retrieval → Generation (+ citations) │
│             → digest → Retrieval → Digest Node              │
│             → trend  → Trend Node (SQL aggregation)         │
│             → (weak) → Live Search Node (Tavily fallback)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  API LAYER  (FastAPI)                        │
│  /chat (SSE streaming) │ /articles │ /trends │ /digest      │
│  /article-chat/:id     │ /admin/ingestion/trigger           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               FRONTEND  (React + Vite)                       │
│  Home Feed │ Article Detail │ Chat │ Digest │ Dashboard     │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Home Feed
- Inshorts-style news cards with real article images, headlines, source, timestamp, and sentiment badge
- Hero featured story at the top
- "Today's Pick" sidebar with the top 5 most recent articles
- Category filter chips (LLMs, Hardware, Startups, Policy, Robotics)
- Click any card to open the Article Detail view

### Article Detail
- Full article content with image, source, and publish date
- Breadcrumb navigation with category context
- **Community Discussion sidebar** — matched Hacker News comments fetched via semantic similarity, showing usernames, comment text, and upvote counts
- **Article Chat sidebar** — ask questions specifically about the current article, with context injected from both the article summary and related community discussion

### Chat Interface (ChatGPT-style)
- Dark sidebar with session history, "New Chat" button, and per-session delete
- Real-time SSE token streaming — responses appear word by word as they generate
- Markdown rendering for bold, lists, and code blocks
- Citation cards below each response (max 3) showing source name and article title
- Suggestion chips on empty state for quick query starting points
- Chat history persisted in localStorage across page navigations
- Conversational memory — follow-up questions understand prior context

### Dashboard
- Sentiment trend line chart over time (by category)
- Article volume bar chart by category
- Source distribution donut chart (NewsAPI vs Reddit vs HN)
- Most discussed topics horizontal bar chart
- "Explain this trend" button — sends aggregated stats to the LLM for natural-language interpretation

### Digest
- Daily AI/Tech digest grouped by category with article summaries
- Date picker to browse past digests
- Share button for copying the digest

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 (Vite), Tailwind CSS v4, Recharts |
| Backend API | FastAPI (Python 3.13, async) |
| Agent Orchestration | LangGraph |
| LLM | Groq → OpenRouter → Gemini (fallback chain) |
| Embeddings | Gemini API (`gemini-embedding-001`) in prod, `all-MiniLM-L6-v2` in dev |
| Vector Database | ChromaDB (local persistence) |
| Relational Database | PostgreSQL via SQLAlchemy + Alembic (Supabase in production) |
| Task Scheduling | Celery + Redis (dev), FastAPI BackgroundTasks (production) |
| News Sources | NewsAPI.ai, newsdata.io, Hacker News API, DEV.to API, RSS feeds |
| Live Search Fallback | Tavily API |
| Auth | JWT (python-jose + bcrypt), single admin user |
| Deployment | Render (backend), Vercel (frontend), Supabase (database) |
| Containerization | Docker + docker-compose (local dev) |

---

## 🗂️ Project Structure

```
newspulse-ai/
├── app/
│   ├── api/endpoints/          # FastAPI route handlers
│   │   ├── chat.py             # SSE streaming chat endpoint
│   │   ├── article_chat.py     # Per-article chat endpoint
│   │   ├── articles.py         # Feed + article detail endpoints
│   │   ├── trends.py           # Trend/sentiment aggregation
│   │   ├── auth.py             # JWT login/verify
│   │   └── admin.py            # Ingestion trigger + status
│   ├── core/
│   │   ├── config.py           # Pydantic settings (env vars)
│   │   ├── auth.py             # JWT utilities + dependencies
│   │   └── llm.py              # LLM provider routing + fallback
│   ├── db/
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── session.py          # Async DB session (pgBouncer safe)
│   │   └── vector_store.py     # ChromaDB client wrapper
│   ├── ingestion/              # Data ingestion layer
│   │   ├── pipeline.py         # Orchestrator
│   │   ├── newsdata_ingester.py
│   │   ├── newsapi_ingester.py
│   │   ├── hackernews_ingester.py
│   │   ├── devto_ingester.py
│   │   ├── rss_ingester.py
│   │   ├── tavily_ingester.py
│   │   ├── normalizer.py       # Common Article schema
│   │   └── deduplicator.py     # URL + fuzzy title dedup
│   ├── processing/             # Enrichment layer
│   │   ├── classifier.py       # Category tagging
│   │   ├── summarizer.py       # Abstractive summarization
│   │   ├── sentiment.py        # Sentiment analysis
│   │   ├── embedder.py         # Dual-backend embedding
│   │   └── indexer.py          # Supabase + ChromaDB write
│   ├── rag/                    # LangGraph agentic pipeline
│   │   ├── graph.py            # Graph definition + edges
│   │   ├── state.py            # RAGState TypedDict
│   │   ├── nodes/              # Router, Retrieval, Generation,
│   │   │                       # Digest, Trend, LiveSearch nodes
│   │   └── prompts/            # System prompt templates
│   ├── scheduler/              # Celery (dev only)
│   │   ├── celery_app.py
│   │   ├── tasks.py
│   │   └── beat_schedule.py
│   └── main.py                 # FastAPI app entrypoint
├── frontend/
│   └── src/
│       ├── pages/              # FeedPage, ChatPage, ArticleDetailPage,
│       │                       # DigestPage, DashboardPage, LoginPage
│       ├── components/         # Navbar, NewsCard, ChatBubble,
│       │                       # CitationCard, ArticleChatSidebar, etc.
│       ├── hooks/              # useChatStream, useArticles, useApiHealth
│       ├── api/                # chatApi.js, articleChatApi.js
│       └── utils/              # auth.js, sessionStorage.js
├── alembic/                    # Database migration scripts
├── scripts/                    # Utility scripts (recreate_db, reindex)
├── Dockerfile
├── docker-compose.yml          # Local dev orchestration
├── render.yaml                 # Render deployment config
└── requirements.txt
```

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.13+
- Node.js 18+
- Docker Desktop
- PostgreSQL (local instance)

### 1. Clone the repository
```bash
git clone https://github.com/Prathamesh2403/NewsPulseAI.git
cd NewsPulseAI
```

### 2. Backend setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in your API keys
cp .env.example .env
```

### 3. Configure environment variables
Edit `.env` with your keys:
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/newspulse

# LLM
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key

# News APIs
NEWSDATA_API_KEY=your_key
NEWSAPI_KEY=your_key
TAVILY_API_KEY=your_key

# Auth
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=   # generate with: python scripts/generate_password_hash.py
JWT_SECRET_KEY=        # generate with: python -c "import secrets; print(secrets.token_hex(32))"

# App
ENVIRONMENT=development
REDIS_URL=redis://localhost:6379/0
```

### 4. Run database migrations
```bash
alembic upgrade head
```

### 5. Start all services with Docker
```bash
# Starts FastAPI + Celery Worker + Celery Beat + Redis
docker-compose up --build
```

Or run individually in separate terminals:
```bash
# Terminal 1 — Redis
docker run -p 6379:6379 redis

# Terminal 2 — FastAPI
uvicorn app.main:app --reload

# Terminal 3 — Celery Worker
celery -A app.scheduler.celery_app worker --loglevel=info --pool=solo -Q news_bot

# Terminal 4 — Celery Beat (scheduler)
celery -A app.scheduler.celery_app beat --loglevel=info
```

### 6. Run initial ingestion
```bash
python scripts/run_all_ingestion.py
```

Or trigger via API after starting the server:
```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your_password"}'

# Trigger ingestion with token
curl -X POST http://localhost:8000/api/v1/admin/ingestion/trigger \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 7. Frontend setup
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 🌍 Production Deployment

### Stack
| Service | Platform |
|---|---|
| Frontend | Vercel |
| Backend API | Render (Free Web Service) |
| Database | Supabase (PostgreSQL) |
| Vector Store | ChromaDB (ephemeral, synced on deploy) |
| Ingestion Schedule | Render Cron Job (every 12 hours) |

### Key production differences from development
- Celery and Redis are **not used** in production — ingestion runs as a FastAPI `BackgroundTask` through cron jobs every 12 hr
- Embeddings use **Gemini API** instead of local SentenceTransformer (avoids 512MB RAM limit on Render free tier)
- Database uses **Supabase** with pgBouncer session pooling (`statement_cache_size=0` to prevent prepared statement conflicts)
- ChromaDB is ephemeral on Render free tier — call `/api/v1/admin/ingestion/sync-chroma` after each redeploy to repopulate from Supabase

### Deploy your own instance

**Backend (Render):**
1. Fork this repo
2. Connect to Render → New Web Service → select your fork
3. Runtime: Docker, Branch: main
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `.env.production.example`

**Frontend (Vercel):**
1. New Project → import forked repo
2. Root directory: `frontend`
3. Add env var: `VITE_API_BASE_URL=https://your-render-url.onrender.com`
4. Deploy
