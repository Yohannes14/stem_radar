# STEM RADAR — System Architecture & Developer Guide

## 1. System Overview & Vision

**STEM RADAR** is an enterprise-grade AI-powered STEM and Technology Intelligence Hub designed to discover, organize, analyze, rank, and present scientific breakthroughs and technological innovations.

The platform is designed around the **Clean Architecture / Modular Monolith** paradigm:
- **Core Domain:** Pure Python business logic with zero framework dependencies (`app/core/taxonomy.py`, `app/processors/`).
- **Data Persistence:** SQLAlchemy 2.0 async engine with SQLite / PostgreSQL compatibility via the Repository Pattern (`app/database/`).
- **Application Services:** Cross-cutting workflow coordination (`app/services/`).
- **Presentation Adapters:**
  1. **Telegram Bot Layer (`app/bot/`):** Asynchronous interactive bot powered by `python-telegram-bot` 21+, featuring debounced callback routing and resilient error fallback.
  2. **FastAPI REST API Layer (`app/api/`):** High-throughput OpenAPI v3 interface with API key auth and sliding-window rate limiting.

```
                              ┌─────────────────────────────────────────┐
                              │           Clients & Consumers           │
                              └─────────────┬───────────────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
        ┌─────────────────────────┐                   ┌─────────────────────────┐
        │   Telegram Bot Layer    │                   │   FastAPI REST API      │
        │  (python-telegram-bot)  │                   │       (OpenAPI)         │
        └────────────┬────────────┘                   └────────────┬────────────┘
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                              ┌───────────────────────────┐
                              │    Application Services   │
                              │  (Search, AI, Automation, │
                              │   StudentHub, News)       │
                              └─────────────┬─────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
        ┌─────────────────────────┐                   ┌─────────────────────────┐
        │     Domain Logic        │                   │    Persistence Layer    │
        │  (Taxonomy, Classifier, │                   │  (Repository Pattern,   │
        │   Ranker, Deduplicator) │                   │   SQLAlchemy 2.0 Async) │
        └─────────────────────────┘                   └─────────────────────────┘
```

---

## 2. Central Information Architecture (The 8 Flagship Hubs)

The user journey is anchored around **8 primary hubs**, reachable via `/menu` or direct slash commands. Navigation guarantees **zero dead-ends** via `nav_back_home_row` controls (`⬅️ Back` and `🏠 Main Menu`).

```
                              ┌─────────────────────┐
                              │      Main Menu      │
                              │     (/menu, /start) │
                              └──────────┬──────────┘
         ┌────────────┬───────────┬──────┴────┬───────────┬────────────┬────────────┐
         ▼            ▼           ▼           ▼           ▼            ▼            ▼
    🧭 Discover   🔬 STEM     📄 Research 🎓 Student  💡 Learn     🔍 Search   ⭐ My Space
       Hub        Tech Hub       Hub         Hub       Academy       Engine      Control
    (/discover)   (/stem)     (/research) (/student)   (/learn)     (/search)   (/myspace)
```

### Hub Responsibilities:
1. **🧭 Discover Hub (`menu:discover`):** Real-time pulse, morning executive briefings (`/briefing`), trending breakthroughs (`/trending`), Technology Radar maturity mapping (`/radar`), and publishing velocity (`/velocity`).
2. **🔬 STEM & Technology Hub (`menu:stem_tech`):** Deep dives across the 12 foundational STEM disciplines and regional technology ecosystems.
3. **📄 Research & Innovation Hub (`menu:research`):** Peer-reviewed arXiv literature (`/research`), empirical 6-dimension paper analyses, and GitHub replication repositories.
4. **🎓 Student Hub (`menu:student_hub`):** Verified STEM scholarships (`/scholarships`), university admissions guidelines (`/universities`), free online courses (`/courses`), and deadline countdowns (`/deadlines`).
5. **💡 Learn STEM Academy (`menu:learn`):** Structured 3-tier curriculum paths (`🐣 Beginner`, `🧑‍💻 Intermediate`, `🔬 Advanced`), hands-on engineering lab projects (`/project`), multiple-choice quizzes (`/quiz`), architectural comparisons (`/compare`), and progress mastery (`/progress`).
6. **🔍 Search & Discovery Engine (`menu:search`):** Unified multi-domain database search (`/search`), resilient external live web search fallback (`/websearch`), and multi-source AI briefings with citations (`/search_ai`).
7. **⭐ My Space (`menu:myspace`):** Bookmarks (`/saved`), active topic subscriptions (`/interests`), technology keyword watchlists (`/watchlist`), quiet hours & notification cadence (`/settings`), GDPR data export (`/export`), and feedback (`/feedback`).
8. **❓ Command Help (`menu:help`):** Comprehensive interactive catalog and system telemetry.

---

## 3. Central Taxonomy System (`app/core/taxonomy.py`)

Knowledge is organized under a single authoritative taxonomy defining **12 foundational disciplines** and **4 cross-cutting domains**:

| Discipline Name | Canonical Slug | Emoji | Primary Focus |
| :--- | :--- | :---: | :--- |
| **Artificial Intelligence & Data Science** | `ai` | 🤖 | GenAI, LLMs, AI Agents, ML, Deep Learning, Vision, NLP, Safety |
| **Computer Science** | `computer-science` | 💻 | Algorithms, OS, Distributed Systems, Networks, DBs |
| **Software Engineering & Architecture** | `software-engineering`| ⚙️ | Backend Architecture, Cloud, DevOps, Web & Mobile, Open Source |
| **Cybersecurity & Privacy** | `cybersecurity` | 🛡️ | AppSec, NetSec, Cryptography, CloudSec, Threat Intel |
| **Robotics & Autonomous Systems** | `robotics` | 🦾 | Industrial Robotics, Humanoids, Drones, ROS, Controls |
| **Electronics & Embedded IoT** | `electronics` | ⚡ | Microcontrollers, PCB, Sensors, IoT, FPGA, Hardware Design |
| **Applied Engineering** | `mechanical-engineering`| 🏗️ | Mechanical, Electrical, Civil, Aerospace, Materials |
| **Natural Sciences & Mathematics** | `physics` | 🔬 | Physics, Chemistry, Molecular Biology, Mathematics, Astronomy |
| **Space & Aerospace Technology** | `space-technology` | 🚀 | Space Exploration, Satellites, Rocketry, Orbital Mechanics |
| **Energy & Climate Technology** | `renewable-energy` | 🌱 | Solar, Wind, Battery Storage, CleanTech, Sustainability |
| **Biotechnology & Health Tech** | `biotechnology` | 🧬 | Bioinformatics, Genetic Engineering, Biomedical Devices |
| **Frontier & Emerging Tech** | `emerging-tech` | ✨ | Quantum Computing, Nanotechnology, 3D Printing, BCIs |
| **Ethiopia Tech Ecosystem** | `ethiopia-tech` | 🇪🇹 | Startups, Fintech, Digital Transformation, Local R&D |
| **Ethiopian Regional Affairs** | `ethiopia-affairs` | 🇪🇹 | Science, Policy, Infrastructure, Socio-Technical Affairs |
| **Global Technology Politics** | `global-politics` | 🌍 | Tech Geopolitics, Semiconductor Supply Chains |
| **Technology Policy & Ethics** | `tech-policy` | ⚖️ | AI Governance, Algorithmic Transparency, Data Sovereignty |

---

## 4. Multi-Domain Search & External Provider Registry

The search pipeline is managed by `SearchService` in `app/services/search/`:

```
User Query: "/search quantum cryptography"
                       │
                       ▼
          ┌───────────────────────────┐
          │       SearchService       │
          └─────────────┬─────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐         ┌───────────────────────────────┐
│ Database Search  │         │ ExternalSearchRegistry        │
│ (Articles, arXiv,│         │ (Fallback & Live Web Search)  │
│  Scholarships)   │         └───────────────┬───────────────┘
└──────────────────┘                         │
                             ┌───────────────┼───────────────┐
                             ▼               ▼               ▼
                        DuckDuckGo       Wikipedia    Semantic Scholar
                         (Default)       (Default)    (Optional API)
                             │               │
                             ▼               ▼
                        Brave Search    Google Search
                       (Optional API)  (Optional API)
```

- **Resilience:** Providers implement a `BaseSearchProvider` abstract interface with circuit-breaking timeouts (`EXTERNAL_SEARCH_TIMEOUT_SECONDS = 4.0s`).
- **Fallback Guarantee:** Zero-configuration public providers (**DuckDuckGo** and **Wikipedia**) function out-of-the-box with 0 API keys required.
- **AI Synthesis (`SearchAiAssistant`):** Grounded summarization synthesizing local database findings and external web sources into structured takeaways with citations.

---

## 5. Verification & Academic Truth Standards

### Student Hub Opportunities
To prevent academic misinformation:
- **Mandatory Truth Metadata:** Every scholarship and grant contains `truth_rating`, `verification_status`, `verified_by`, `last_verified_at`, `official_source_url`, and `official_application_url`.
- **Status Indicators:**
  - `🟢 VERIFIED`: Manually reviewed by administrators or verified against official institutional portals.
  - `🟡 UNVERIFIED COMMUNITY SUBMISSION`: Submissions awaiting moderation review.
  - `🔴 EXPIRED`: Deadlines that have passed are clearly marked with warning badges to avoid wasted student effort.
- **Zero Fabrication:** The AI and scrapers are strictly prohibited from generating synthetic deadlines or financial promises.

### Research Pre-Prints (arXiv)
- **Academic Integrity Disclaimer:** Prominently warns readers that AI breakdowns are analytical aids and do not substitute for reading peer-reviewed source literature.
- **Replication Code Extraction:** Automated heuristics search arXiv abstracts and metadata for open-source repositories (GitHub/GitLab) and include direct replication links.

---

## 6. Testing, Quality & Developer Experience

The repository maintains an automated test suite with **294+ tests** across **39 test modules**:

```bash
# Execute full test suite
pytest

# Static analysis and linting
ruff check .

# Formatting
ruff format .
```

- **100% Mocked Network Boundaries:** No test ever performs external HTTP requests or touches live Telegram servers.
- **In-Memory SQLite Sessions:** Database tests run in isolated async sessions ensuring complete idempotence and zero side effects.
- **Sub-5-Second Test Execution:** Entire 294-test suite runs in under 5 seconds.

