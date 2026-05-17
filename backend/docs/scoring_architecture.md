# CyberBoyAI — Scoring Architecture & Logic

This document explains the mathematical and logical distinction between **Local Agent Risk** and **Global System Confidence**.

---

## 1. Local ML Risk (The "Structural DNA")
**Scope:** Single Agent (`MLAgent`)
**Calculation Source:** Random Forest Classifier (`models/model.joblib`)

### How it is calculated:
The ML Agent extracts **17 structural features** from the raw URL string. It doesn't know who owns the site or what is on the page; it only knows how the link is "built."

| Feature | Description |
| :--- | :--- |
| **Entropy** | Measures the randomness of the domain string. High entropy (>4.5) suggests DGA (Randomly generated domains). |
| **TLD Risk** | Assignments based on TLD reputation (e.g., `.top`, `.xyz`, `.ml` score higher than `.com`). |
| **Numerical Sub** | Checks for "leet-speak" substitutions (e.g., `am0zon` instead of `amazon`). |
| **Subdomain Depth** | Measures nesting (e.g., `login.security.verify.account.com` is extremely high risk). |

**The Result:** A probability score (0.0 to 1.0). If you see **"Classified as phishing (97.4% risk)"**, it means the model is 97.4% certain that this URL matches the physical structure of a typical phishing link.

---

## 2. Global Confidence (The "Consensus Score")
**Scope:** System-wide (`VerdictEngine`)
**Calculation Score:** Weighted Fusion of 8 Security Layers

### How it is calculated:
The system doesn't trust any single agent blindly. It uses a **Consensus-Aware Weighted Formula** to combine results from all 8 layers:

| Layer Category | Weighted Contribution (Approx) |
| :--- | :--- |
| **Intelligence Feeds** | 35% (Google GSB, PhishTank, OTX, Community) |
| **Brand Analysis** | 30% (Fuzzy matching vs. Known Brands) |
| **AI Forensic Analysis** | 20% (GPT-4o Visual & Textual Reasoning) |
| **ML Structural DNA** | 15% (Random Forest Score) |

### The Confidence Formula:
The "Confidence" you see in the UI is a **meta-metric** derived from the final fused score:
- **For DANGEROUS/SUSPICIOUS**: Confidence = `Final Score * 100`. (If the system says it's 80% likely to be a threat, we are "80% Confident" it is a threat).
- **For SAFE**: Confidence = `(1.0 - Final Score) * 100`. (If the threat score is only 0.02, we are "98% Confident" it is safe).

---

## 3. Why the numbers sometimes "Disagree"
It is common to see a **98% ML Risk** but only **51% Global Confidence**. This happens during a **Consensus Conflict**:

### Scenario: A Legitimate URL Shortener (`bit.ly`)
1.  **ML Agent (98%)**: "This looks like a short, obfuscated link used by hackers!"
2.  **Brand Agent (0%)**: "Matches the official Bitly domain label."
3.  **AI Agent (0%)**: "I visited the page; it's the real Bitly 404/Login page."
4.  **Lookup Agent (0%)**: "Not found in any blacklist."

**The Conflict Resolution:** 
The Verdict Engine sees that the ML is screaming "Danger" but the other 7 layers are saying "Safe." It mediates this by giving a **Stalemate Score** (around 0.50). 
- The UI shows **"SUSPICIOUS"** with **50% Confidence**.
- This tells the user: *"One part of our brain thinks this is a threat, but the rest isn't so sure. Tread carefully."*

### 4. Fast-Path Overrides
The system has "Absolute Truth" rules that override all calculations:
- **Whitelist Override**: If the domain is in our `trusted_domains` database, the score is forced to **0.02 (SAFE)** regardless of ML/AI noise.
- **Blacklist Override**: If the domain is in a verified threat database (e.g., PhishTank), the score is forced to **1.0 (DANGEROUS)** instantly.

---
*Document Version: 1.1*
*Last Updated: 2026-05-13*
