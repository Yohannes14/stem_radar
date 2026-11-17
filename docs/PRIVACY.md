# STEM RADAR — Privacy Policy

**Effective Date:** November 16, 2026  
**Platform:** STEM RADAR (Telegram Bot & FastAPI Intelligence Platform)  
**Status:** Public Release

---

## 1. Our Privacy Commitment

STEM RADAR is an AI-powered STEM and technology intelligence platform designed for researchers, software engineers, students, and technology leaders. We treat privacy as a fundamental architectural requirement, not an afterthought.

This platform operates on a **privacy-by-design** and **data-minimization** principle: we only collect the minimum telemetry required to personalize news feeds, deliver scheduled briefings, and track educational learning progress.

---

## 2. Information We Collect

### A. Telegram User Metadata
When you initiate an interaction with the Telegram bot (`/start` or any command), the platform records:
- **Telegram User ID**: Numeric identifier used exclusively to deliver requested messages, alerts, and executive briefings.
- **Username & Name**: Used to personalize greetings in briefings and digests (e.g., *"Good morning, Alan"*).
- **Last Active Timestamp**: Used to maintain active session state and prune abandoned notifications.

### B. User Personalization Preferences
- **Subscribed STEM Domains**: Categories you subscribe to (e.g., Artificial Intelligence, Robotics, Quantum Computing) to bias ranking and briefing relevance.
- **Notification Settings**: Delivery toggle, scheduled morning digest time, and configured quiet hours (e.g., `22:00` to `07:00 UTC`).
- **Saved Bookmarks**: Articles and research papers you explicitly save via the `⭐ Bookmark` inline button.
- **Watchlist Keywords**: Specific technical keywords you monitor for instant high-impact alerts (`/watchlist add <keyword>`).
- **Educational Progress**: Lessons completed, quizzes taken, and comprehension scores (`/progress`).

### C. Feedback & Communications
- User-submitted messages sent via `/feedback <message>`.

---

## 3. What We Never Collect or Do

1. **No Sensitive Personal Attributes**: We never request, infer, or store biometric, financial, location, political, or sensitive personal data.
2. **No External Tracking**: We do not monitor your browsing behavior outside the bot or app interfaces.
3. **No Cross-User Data Exposure**: Your saved bookmarks, watchlists, preferences, and progress are strictly isolated to your user ID and are never exposed to other users.
4. **No Commercial Data Reselling**: We never sell, lease, or monetize user data with third-party advertisers or data brokers.
5. **No Credential Logging**: Passwords, API keys, and environment secrets are never logged or stored in plain-text records.

---

## 4. AI Provider Privacy & Prompt Sanitization

STEM RADAR utilizes AI models (such as OpenAI GPT-4o-mini or configured LLM providers) to synthesize multi-tier technical explanations, paper analyses, and lesson roadmaps:
- **No Personal Identifiers in Prompts**: Prompts sent to AI engines contain only sanitized article text, research abstracts, or domain keywords. Your Telegram ID, username, or personal metadata is never included in AI model requests.
- **Enterprise API Zero-Data Retention**: AI requests are dispatched via official developer APIs governed by business terms where customer inputs are not used for public model training.

---

## 5. Data Storage, Security & SQLite Hardening

- **Database Engine**: Production data is stored in an encrypted/restricted filesystem SQLite database utilizing **Write-Ahead Logging (WAL)** mode.
- **Connection Isolation**: Concurrency controls enforce foreign key validation, strict busy-wait timeouts (`5000ms`), and normalized synchronicity.
- **Role-Based Access Control**: Administrative maintenance operations (`/collect`, `/ban`, `/unban`) are restricted strictly to authorized platform administrators.

---

## 6. User Rights & Data Governance (GDPR / CCPA Alignment)

Under privacy regulations and our core principles, you maintain full sovereignty over your data:

| Action | Telegram Command | REST API Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Data Inspection** | `/settings` | `GET /api/v1/user/interests` | Review active category subscriptions and quiet hours |
| **Data Export** | `/export` | `GET /api/v1/user/bookmarks` | Export a machine-readable JSON copy of all your stored data |
| **Data Deletion** | `/delete_account confirm` | `DELETE /api/v1/user/bookmarks/{id}` | Permanently purge all your preferences, bookmarks, watchlists, and history |

### Complete Deletion Procedure
Executing `/delete_account confirm` triggers an atomic transaction that removes all records associated with your Telegram User ID across:
- `saved_articles`
- `user_preferences`
- `user_watchlists`
- `user_learning_progress`
- `user_feedback`
- `notification_logs`

---

## 7. Contact & Support

For privacy inquiries, security reports, or technical support, submit feedback via `/feedback` or contact the repository maintainers.

