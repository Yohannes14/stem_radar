# STEM RADAR 📡
### Enterprise AI-Powered STEM & Technology Intelligence Hub

**Discover. Understand. Learn. Research. Innovate.**

STEM RADAR is a multidisciplinary technology intelligence and educational platform supporting both an interactive **Telegram Bot** and a high-performance **FastAPI REST API**. It aggregates, categorizes, deduplicates, analyzes, ranks, and synthesizes high-impact developments, research literature, academic opportunities, and interactive engineering labs across **12 foundational STEM disciplines** and **4 cross-cutting domains**.

---

## 🏛️ Clean Architecture / Modular Monolith

```
stem-radar/
├── app/
│   ├── main.py                  # CLI & Telegram runtime entry point
│   ├── config.py                # Configuration and logging shims
│   │
│   ├── core/                    # Core Infrastructure & Cross-Cutting Concerns
│   │   ├── config.py            # Pydantic Settings (API, Telegram, DB, AI, External Search)
│   │   ├── taxonomy.py          # Central STEM taxonomy (12 disciplines + 4 domains)
│   │   ├── exceptions.py        # Domain-driven Exception hierarchy
│   │   └── logging.py           # Standardized structured logging
│   │
│   ├── database/                # Persistence & Data Access Layer
│   │   ├── models.py            # SQLAlchemy 2.0 ORM models (Article, Opportunity, Resource, etc.)
│   │   ├── database.py          # Async engine, connection pooling, SQLite migrations
│   │   └── repository.py        # Asynchronous Repository pattern
│   │
│   ├── collectors/              # Multi-Source Ingestion Pipeline
│   │   ├── base.py              # BaseCollector interface & CollectedArticle schema
│   │   ├── client.py            # Resilient HTTP client with retry & exponential backoff
│   │   ├── rss_collector.py     # High-throughput RSS / Atom parser
│   │   ├── arxiv_collector.py   # Official arXiv API paper ingestor
│   │   └── github_collector.py  # Trending GitHub repository monitor
│   │
│   ├── processors/              # Pure Domain Business Logic
│   │   ├── classifier.py        # Central taxonomy classifier (tokenization, aliases, scoring)
│   │   ├── deduplicator.py      # Tracking param stripping & URL SHA-256 hashing
│   │   └── ranking.py           # Multi-factor intelligence ranking engine (ArticleRanker)
│   │
│   ├── services/                # Shared Application Services
│   │   ├── news_service.py      # Multi-source ingestion & query service
│   │   ├── student_hub_service.py # Scholarships, opportunities, admissions, courses
│   │   ├── automation_service.py# Executive briefings, watchlists, quiet hours & scoring
│   │   ├── content_service.py   # STEM content opportunity generator
│   │   ├── search/              # Unified Multi-Domain & External Web Search
│   │   │   ├── service.py       # Multi-domain database search (Articles, arXiv, Scholarships)
│   │   │   ├── ai_assistant.py  # Grounded multi-source AI synthesis with citations
│   │   │   └── providers/       # Resilient search providers (DuckDuckGo, Wikipedia, Scholar, Brave, Google)
│   │   └── ai/                  # Modular AI Intelligence Engine
│   │       ├── service.py       # Summaries, 6-D paper analysis, concept explainer, labs
│   │       ├── schemas.py       # Pydantic structured DTOs
│   │       ├── cache.py         # SHA-256 TTL response cache
│   │       ├── cost_tracker.py  # Token accounting and cost estimation
│   │       └── adapters/        # OpenAI adapter & deterministic heuristic fallback engines
│   │
│   ├── bot/                     # Adapter 1: Telegram Presentation Layer
│   │   ├── bot.py               # Bot builder, lifecycle & error handlers
│   │   ├── filters/             # Authentication & role-based access control
│   │   ├── handlers/            # Handlers (base, news, student_hub, education, settings, etc.)
│   │   ├── keyboards/           # Interactive inline keyboards & navigation
│   │   └── ui/                  # Formatters, menus, empty states, and debouncers
│   │
│   └── api/                     # Adapter 2: FastAPI REST API Layer
│       ├── main.py              # FastAPI application factory & async lifespan
│       ├── dependencies.py      # Dependency injection (DB session, auth, services)
│       ├── exceptions.py        # Centralized exception handlers & error envelopes
│       ├── middleware/          # Request logging & in-memory sliding-window rate limiter
│       └── v1/
│           ├── router.py        # V1 aggregation router
│           ├── endpoints/       # Route handlers (news, research, scholarships, search, ai, radar)
│           └── schemas/         # Pydantic DTOs & response schemas
│
├── bot.py                       # Standalone Telegram Bot launcher
├── api.py                       # Standalone FastAPI server launcher
├── tests/                       # 294 Automated tests (100% mocked, 0 external network dependencies)
├── data/                        # Persistent local SQLite storage
├── Makefile                     # Developer productivity shortcuts
├── requirements.txt             # Pinned project dependencies
└── pyproject.toml               # Build, pytest, and ruff configuration
```

---

## 🧭 Flagship 8-Hub Information Architecture

The Telegram Bot is structured around **8 dedicated intelligence hubs**, designed for progressive disclosure and zero dead-ends:

| Hub | Purpose | Flagship Commands |
| :--- | :--- | :--- |
| **🧭 Discover Hub** | Daily executive briefings, trending SOTA breakthroughs, Technology Radar, and domain publishing velocity. | `/discover`, `/briefing`, `/trending` |
| **🔬 STEM & Technology** | Comprehensive intelligence across 12 foundational STEM disciplines and regional technology developments. | `/stem`, `/news` |
| **📄 Research & Innovation** | Peer-reviewed research, arXiv pre-prints, 6-dimension empirical paper breakdowns, and replication repositories. | `/research`, `/explain` |
| **🎓 Student Hub** | Truth-verified scholarships, university admissions, deadlines tracker, and open educational resources. | `/student`, `/scholarships`, `/courses`, `/deadlines`, `/universities` |
| **💡 Learn STEM** | STEM Learning Academy featuring 3 difficulty tiers (`🐣`, `🧑‍💻`, `🔬`), interactive labs, quizzes, and roadmaps. | `/learn`, `/roadmap`, `/project`, `/quiz`, `/compare`, `/progress` |
| **🔍 Search & Web Discovery** | Instant multi-domain database search + live web fallback (DuckDuckGo, Wikipedia) + grounded AI synthesis. | `/search`, `/websearch`, `/search_ai` |
| **⭐ My Space** | Personal control center: saved bookmarks, subscriptions, active watchlists, quiet hours, GDPR export, and feedback. | `/myspace`, `/saved`, `/watchlist`, `/settings`, `/export`, `/feedback` |
| **❓ Command Help** | Accessible interactive command catalog, system status, and onboarding guidance. | `/help`, `/start`, `/sources`, `/collect` |

---

## 🏷️ Central STEM Taxonomy (12 + 4 Disciplines)

Managed through [`app/core/taxonomy.py`](app/core/taxonomy.py), the platform organizes all knowledge into **12 foundational disciplines** and **4 cross-cutting domains**:

### 12 Foundational STEM Disciplines
1. **🤖 Artificial Intelligence & Data Science:** Generative AI, LLMs, AI Agents, Machine Learning, Deep Learning, Computer Vision, NLP, AI Safety.
2. **💻 Computer Science:** Algorithms, Data Structures, Operating Systems, Computer Systems, Databases, Distributed Systems.
3. **⚙️ Software Engineering & Architecture:** Backend Architecture, Cloud & Distributed Systems, Web & Mobile Development, DevOps, Open Source.
4. **🛡️ Cybersecurity & Privacy:** Network Security, Application Security, Cryptography, Cloud Security, Threat Intelligence, Digital Forensics.
5. **🦾 Robotics & Autonomous Systems:** Industrial Robotics, Humanoid Robotics, Autonomous Vehicles, Drones, Robot Operating Systems (ROS).
6. **⚡ Electronics & Embedded IoT:** Microcontrollers, Embedded Programming, PCB Design, Sensors, IoT, FPGA, Hardware Design.
7. **🏗️ Applied Engineering:** Mechanical Engineering, Electrical Engineering, Civil & Structural, Chemical, Aerospace, Biomedical.
8. **🔬 Natural Sciences & Mathematics:** Physics, Chemistry, Molecular Biology, Mathematics, Astronomy, Earth & Environmental Sciences.
9. **🚀 Space & Aerospace Technology:** Space Exploration, Satellites, Rocket Technology, Orbital Mechanics, Space Science.
10. **🌱 Energy & Climate Technology:** Renewable Energy, Solar & Wind, Battery Tech, Energy Storage, CleanTech, Sustainability.
11. **🧬 Biotechnology & Health Technology:** Bioinformatics, Genetic Engineering, Synthetic Biology, Biomedical Devices, HealthTech.
12. **✨ Frontier & Emerging Technologies:** Quantum Computing, Nanotechnology, Advanced Materials, Brain-Computer Interfaces, 3D Printing.

### 4 Cross-Cutting & Regional Domains
- **🇪🇹 Ethiopia Tech Ecosystem:** Startups, digital transformation, fintech, and local innovation.
- **🇪🇹 Ethiopian Regional Affairs:** Science, socio-technical development, and infrastructure.
- **🌍 Global Technology Politics:** Geopolitics of technology, chip supply chains, and global governance.
- **⚖️ Technology Policy & Ethics:** AI regulation, algorithmic transparency, data sovereignty, and open access.

---

## 🔍 Multi-Domain & Live Web Search Engine

STEM RADAR provides a three-tiered discovery system:

1. **Multi-Domain Database Search (`/search <query>`):**
   - Concurrent, full-text ranking across Articles, arXiv Research, and Student Hub Opportunities.
   - Inline category badges and unified pagination.
2. **Live External Web Fallback (`/websearch <query>`):**
   - Seamlessly queries the **ExternalSearchRegistry** across external providers.
   - Built-in zero-config providers: **DuckDuckGo** and **Wikipedia**.
   - Optional API-backed providers: **Semantic Scholar**, **Brave Search**, and **Google Custom Search**.
3. **Multi-Source AI Intelligence Synthesis (`/search_ai <topic>`):**
   - Grounded multi-source retrieval synthesizing database records and live web citations into executive summaries with key takeaways.

---

## 🎓 Student Hub: Trust & Verification Standards

To prevent misinformation, all opportunities adhere to strict academic integrity rules:
- **Verified Metadata:** Every opportunity includes official provider, announcement URL, application URL, study level, funding coverage, opening/closing dates, last verified timestamp, and verification status.
- **Truth Ratings:** Badges clearly communicate verification (`🟢 VERIFIED`, `🟡 UNVERIFIED COMMUNITY SUBMISSION`, `🔴 EXPIRED`).
- **Zero Fabrication:** The system never invents deadlines, funding coverage, or eligibility criteria. If a deadline has passed, it is prominently tagged with a closed indicator.

---

## 📄 Research & arXiv Scientific Experience

- **Academic Integrity Policy:** Explicitly disclaims that AI-generated breakdowns are analytical study aids and do not replace peer-reviewed literature.
- **6-Dimension Empirical Analysis:**
  1. *Core Problem & Motivation*
  2. *Proposed Methodology & Architecture*
  3. *Key Findings & Empirical Metrics*
  4. *Identified Limitations & Failure Modes*
  5. *Open Research Questions & Next Steps*
  6. *Replication & Code Repository Links* (automatically parses GitHub/GitLab repositories).

---

## 💡 STEM Learning Academy & Engineering Labs

- **3 Difficulty Paths:** Beginner (`🐣`), Intermediate (`🧑‍💻`), Advanced (`🔬`).
- **Interactive Project Generator (`/project <topic>`):** Generates production-grade portfolio engineering labs including:
  - *Problem Statement & System Architecture*
  - *Recommended Tech Stack & Bill of Materials*
  - *Step-by-Step Implementation Milestones*
  - *Estimated Completion Timeline*
  - *Target Learning Outcomes*
  - *Verification & Testing Procedures*
  - *Common Pitfalls to Avoid*
  - *Hiring Portfolio Talking Points*

---

## ⚙️ Personalization, Privacy & GDPR Controls

- **Cadence & Quiet Hours:** Dedicated quiet hours toggle (`toggle_quiet`) allows silencing notifications during local rest periods (default `22:00`–`07:00` UTC).
- **Data Portability (`/export`):** Complete machine-readable JSON export of stored preferences, bookmarks, watchlists, and learning progress.
- **Right to Erasure (`/delete_account`):** Instantly purges personal data upon user confirmation.
- **Community Feedback (`/feedback`):** Direct in-bot feedback pipeline to platform administrators.

---

## ⚡ Developer Commands (Makefile)

| Command | Action |
| :--- | :--- |
| `make install` | Install dependencies into virtual environment |
| `make run` | Start the Telegram Bot |
| `make run-api` | Start the FastAPI REST Server (`http://127.0.0.1:8000`) |
| `make collect` | Run a one-shot multi-source intelligence collection |
| `make init-db` | Initialize database schema and seed default STEM categories |
| `make test` | Execute the full automated pytest suite (294+ tests) |
| `make lint` | Run Ruff static analysis |
| `make format` | Automatically fix and format the codebase with Ruff |
| `make clean` | Clean up cache and temporary files |

---

##  Getting Started

### 1. Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
```ini
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_token_from_botfather
ALLOWED_TELEGRAM_USER_IDS=your_telegram_id

# Database
DATABASE_URL=sqlite+aiosqlite:///data/stem_radar.db

# FastAPI REST Server & Security
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your_secure_api_key_here
API_ADMIN_KEY=your_secure_admin_key_here
API_RATE_LIMIT_PER_MINUTE=60

# Optional AI Configuration (Falls back to deterministic heuristics if unset)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# External Multi-Domain Search Engine (DuckDuckGo & Wikipedia work out-of-the-box)
EXTERNAL_SEARCH_ENABLED=true
EXTERNAL_SEARCH_TIMEOUT_SECONDS=4.0
SEMANTIC_SCHOLAR_API_KEY=
BRAVE_SEARCH_API_KEY=
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
```

### 3. Initialize Database
```bash
make init-db
make collect
```

### 4. Running the Applications
Both applications are **independently runnable** and can run simultaneously on the same database:

- **Run Telegram Bot:**
  ```bash
  make run
  # or: python bot.py
  ```

- **Run FastAPI REST Server:**
  ```bash
  make run-api
  # or: python api.py
  ```

---

## 📖 REST API Documentation

When the FastAPI server is running, interactive OpenAPI documentation is available locally at:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON:** [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

### Available Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/health` | Application status, version, and DB connectivity | No |
| `GET` | `/api/v1/categories` | Complete registry of 12 foundational + 4 regional domains | No |
| `GET` | `/api/v1/news` | Paginated articles with category, source, & search query | No |
| `GET` | `/api/v1/news/{article_id}` | Detailed single article record | No |
| `GET` | `/api/v1/trending` | SOTA breakthroughs ranked by composite impact score | No |
| `GET` | `/api/v1/research` | Scientific research papers from arXiv with abstracts | No |
| `GET` | `/api/v1/scholarships` | Filterable academic opportunities (undergrad, masters, phd) | No |
| `GET` | `/api/v1/search` | Multi-domain search across Articles, arXiv, and Scholarships | No |
| `POST` | `/api/v1/ai/summarize` | Executive AI technical news summary | **Yes** (API Key) |
| `POST` | `/api/v1/ai/explain` | Multi-tier conceptual breakdown (`beginner`, `intermediate`, `advanced`) | **Yes** (API Key) |
| `POST` | `/api/v1/moderation/review`| Admin review and moderation of submitted opportunities | **Yes** (Admin Key)|

---

## 🤖 Telegram Bot Commands Catalog

| Command | Description |
| :--- | :--- |
| `/start` | Welcome screen & frictionless interactive onboarding |
| `/menu` | Flagship 8-Hub main navigation dashboard |
| `/discover` | Discovery pulse (Daily Briefing, Trending SOTA, Radar, Velocity) |
| `/stem` | Explore intelligence across 12 foundational STEM disciplines |
| `/research` | Peer-reviewed research, arXiv literature, and paper breakdowns |
| `/student` | Student Hub dashboard (Scholarships, Admissions, Courses) |
| `/scholarships` | Verified STEM scholarships with country & funding filter cards |
| `/deadlines` | Upcoming application deadlines countdown tracker |
| `/universities` | Accredited STEM university profiles & admission guidelines |
| `/courses` | Free online courses, study materials & learning resources |
| `/submit_opportunity`| Submit an academic opportunity or scholarship for moderation |
| `/learn` | STEM Learning Academy with 3 difficulty curriculum paths |
| `/roadmap` | 4-phase structured engineering learning roadmap |
| `/project` | Production-grade portfolio project generator with verification tests |
| `/quiz` | Interactive multiple-choice comprehension test |
| `/compare` | Architectural concept comparison matrix |
| `/vocabulary` | Domain-specific technical glossary |
| `/progress` | Personal learning mastery and quiz completion score history |
| `/search` | Instant multi-domain database search (Articles, arXiv, Scholarships) |
| `/websearch` | Live external web and academic discovery (DuckDuckGo, Wikipedia) |
| `/search_ai` | Grounded multi-source AI synthesis with citations |
| `/briefing` | Personalized daily executive STEM briefing |
| `/trending` | High-impact developments scored by ArticleRanker |
| `/watchlist` | Manage technology watchlists (`add`, `remove`, `clear`) |
| `/settings` | Preference panel (notifications, quiet hours, domain filters) |
| `/stats` | Platform telemetry and personal intelligence activity |
| `/saved` | View bookmarked articles and saved research papers |
| `/export` | Machine-readable JSON export of personal data (GDPR portability) |
| `/delete_account` | Permanently purge personal account data (Right to Erasure) |
| `/feedback` | Submit suggestions, bug reports, and feedback to engineers |
| `/privacy` | Data protection scope and user privacy rights statement |
| `/sources` | Intelligence feeds health & connectivity telemetry |
| `/collect` | Trigger instant multi-source collection pass |
| `/help` | Comprehensive interactive command catalog |

---

## 🧪 Testing & Verification

The test suite runs 100% mocked without external network dependencies:

```bash
# Run the complete test suite (294+ tests)
make test

# Run Ruff static analysis
make lint

# Automatically format codebase
make format
```
