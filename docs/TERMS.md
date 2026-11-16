# STEM RADAR — Terms of Service

**Effective Date:** November 16, 2026  
**Platform:** STEM RADAR (Telegram Bot & FastAPI Intelligence Platform)  
**Status:** Public Release

---

## 1. Acceptance of Terms

By interacting with the **STEM RADAR** Telegram Bot or querying the **STEM RADAR API**, you agree to these Terms of Service. If you do not agree, please discontinue using the service and execute `/delete_account confirm` to purge your data.

---

## 2. Platform Mission & Service Scope

STEM RADAR is an automated intelligence platform providing:
1. Multi-source STEM and technology news discovery.
2. Academic research paper intelligence (arXiv preprints).
3. Evidence-based Technology Radar and momentum tracking.
4. AI-guided technical explanations and engineering lessons.
5. Practical portfolio engineering project recommendations.

The service is provided for educational, research, and technical intelligence purposes.

---

## 3. Acceptable Use Policy

Users agree to use STEM RADAR responsibly. The following actions are strictly prohibited:

1. **Abusive Automation & Spamming**: Flooding the Telegram bot or API with automated, concurrent, or rapid-fire requests designed to circumvent rate limits or disrupt service availability.
2. **Reverse Engineering & Exploitation**: Attempting to bypass access controls, probe undocumented endpoints, inject malicious prompts (prompt injection attacks), or exfiltrate private configuration secrets.
3. **Harmful Submissions**: Submitting unlawful, defamatory, or abusive messages via feedback or search mechanisms.
4. **Redistribution of Third-Party Articles**: Scraping collected article summaries at scale in violation of original publisher copyrights or terms.

---

## 4. Rate Limits & Quotas

To preserve service availability and manage upstream API quotas:
- **General Commands**: Bound by a sliding-window rate limit (typically 30 requests per minute per user).
- **AI Intelligence Operations**: Bound by adaptive request quotas to prevent resource exhaustion on expensive language model inference.
- **Administrative Operations**: Functions that initiate server-wide network collection (`/collect`, `/refresh`) are restricted exclusively to authorized platform administrators.

Accounts exceeding fair-use limits will be temporarily throttled with a cooling-off message. Chronic abuse may result in permanent suspension via `/ban`.

---

## 5. AI Explanations & Scientific Accuracy Disclaimer

STEM RADAR uses advanced machine learning models to synthesize abstracts, explain concepts, and format educational lessons:

1. **Pedagogical Approximations**: AI-generated explanations are intended as educational aids and conceptual syntheses. While grounded in scientific principles, they may contain simplifications or interpretive nuances.
2. **Researcher Statements vs. AI Analysis**: AI-generated summaries and breakdowns are distinct from empirical claims made by original researchers. Users should always consult the original canonical source URL provided with each article.
3. **No Warranties**: STEM RADAR does not provide engineering warranties or safety-critical certifications. Users implementing suggested project architectures or electronic circuits do so at their own risk and should follow standard electrical, laboratory, and software safety guidelines.

---

## 6. Source Attribution & Intellectual Property

- STEM RADAR does not claim ownership of external articles, research abstracts, or source code reported by third parties.
- All headlines, abstracts, and publisher marks belong to their respective publishers and authors.
- Canonical URLs and clear source attributions are provided on every article card. See [`docs/ATTRIBUTION.md`](file:///Users/ram/Desktop/stem-radar/docs/ATTRIBUTION.md) for licensing details.

---

## 7. Account Suspension & Termination

Platform administrators reserve the right to suspend or permanently ban any user account (`/ban <user_id>`) that violates these Terms of Service, engages in prompt injection attacks, or attempts to disrupt service infrastructure.

---

## 8. Modifications to Terms

We may update these terms as platform capabilities expand. Significant updates will be communicated through Telegram bot announcements and repository change logs.

