# STEM RADAR — Source Attribution & Publisher Compliance

**Status:** Official Compliance Reference  
**Platform:** STEM RADAR Intelligence Engine  

---

## 1. Compliance Philosophy

STEM RADAR aggregates, classifies, and contextualizes state-of-the-art scientific and technological developments. We strictly honor publisher copyrights, academic intellectual property, and external API terms of service.

The platform is designed to **drive discovery toward original sources**, not replace them. Every article card displayed in Telegram or served by the REST API includes:
1. Clear publisher / repository name.
2. Direct canonical URL linking to the original publication (`Read Original 🔗`).
3. Author metadata where supplied by academic feeds.
4. Publication and collection timestamps.

---

## 2. Source Attribution Matrix

| Source / Provider | Ingestion Protocol | Attribution Model | Terms & Licensing Compliance |
| :--- | :--- | :--- | :--- |
| **arXiv.org** | Official arXiv Atom API | Author list, arXiv Paper ID, Category, Abstract, Direct Link | Non-commercial educational use under arXiv API Terms of Use; respectful 3s pacing between query batches. |
| **TechCrunch** | Public RSS 2.0 Feed | Publisher Name, Article Title, Snippet, Canonical Link | Standard syndicated RSS reading terms; full content remains hosted by Yahoo/TechCrunch. |
| **The Verge** | Public RSS Feed | Publisher Name, Article Title, Snippet, Canonical Link | Syndicated RSS guidelines; preserves Vox Media canonical links. |
| **MIT Technology Review** | Public RSS Feed | Publisher Name, Article Title, Snippet, Canonical Link | Syndicated RSS guidelines; links directly to MIT Technology Review articles. |
| **IEEE Spectrum** | Public RSS Feed | Publisher Name, Article Title, Snippet, Canonical Link | Syndicated RSS guidelines; directs users to IEEE Spectrum publications. |
| **GitHub** | Official GitHub REST API | Repository Name, Author/Org, Star Metrics, Direct Repository Link | Complies with GitHub API Terms of Service, respects authenticated/unauthenticated rate limits. |

---

## 3. Publisher Rights & Fair Use Guidelines

STEM RADAR operates under standard fair-use intelligence aggregation practices:
1. **No Paywall Circumvention**: We never scrape paywalled text, bypass authentication gates, or circumvent digital rights management (DRM).
2. **Excerpts & Summaries Only**: The platform stores and indexes title, publication timestamp, and short preview excerpts (typically 1-2 paragraphs). Full reading is redirected to the original publisher URL.
3. **Respect for `robots.txt` & Feed Headers**: Collectors respect HTTP caching headers (`ETag`, `Last-Modified`), request timeouts, and exponential backoff retry policies.

---

## 4. Academic Research (arXiv) Compliance

- **arXiv API Integration**: Research papers are collected from official arXiv feeds (e.g., `cat:cs.AI`, `cat:cs.RO`, `cat:cs.SE`).
- **Research Integrity**: Abstracts and researcher names are reproduced accurately without alteration. Statements made by authors in the paper are clearly distinguished from AI-synthesized pedagogical explanations.
- **Licensing**: arXiv preprints remain the intellectual property of their respective authors under Creative Commons or arXiv non-exclusive distribution licenses.

---

## 5. Untrusted Input & Prompt Injection Defenses

External feeds, titles, abstracts, and RSS descriptions are treated as **untrusted external input**:
1. **Prompt Isolation**: Source content is bound within designated XML/markdown delimiters in AI prompts to prevent prompt injection attacks (e.g., preventing malicious instructions in feed text from hijacking LLM behavior).
2. **Sanitization**: All external titles and descriptions are sanitized against malicious Markdown and HTML tags before rendering to prevent Telegram formatting exploits or link spoofing.
3. **Rate Limiting & Health Monitoring**: Collectors enforce timeouts (30s) and error tracking to isolate misbehaving or compromised feeds automatically.

---

## 6. Notice and Takedown Requests

If you are a publisher, author, or copyright holder and wish to adjust how your feed is indexed or request exclusion from STEM RADAR:
1. Submit an exclusion notice via `/feedback` or repository issue.
2. Verified publisher requests will result in immediate source deactivation via the platform source registry (`is_active = False`).

