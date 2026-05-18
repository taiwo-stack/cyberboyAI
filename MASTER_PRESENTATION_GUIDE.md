# 🛡️ CyberBoyAI: The Ultimate Master Presentation & Architecture Specification

This document is the **absolute master blueprint** for CyberBoyAI. It merges, refines, and synthesizes every single piece of technical architecture, machine learning preprocess/training details, mathematical models, security proofs, and implementation guides into a unified, slide-by-slide structure. 

This guide aligns 100% with the *actual code implementation* in `ml_training/train.py` and `preprocess.py`, including exact datasets, hyperparameters, features, and model configurations.

---

# PART 1: SLIDE-BY-SLIDE PRESENTATION DECK

---

## Slide 1: Title Slide
### 🖥️ Slide Content
*   **Title:** CyberBoyAI: Next-Generation Multi-Agent Cybersecurity Threat Detection & Orchestration Platform
*   **Subtitle:** A 9-Layer Defense-in-Depth System Combining Machine Learning, Live OSINT, and Playwright Sandboxed AI Forensics
*   **Presenter:** [Your Name]
*   **System Status:** Live Production on Vercel (Frontend) and Render (Dockerized FastAPI Backend)
*   **Visual Element:** Sleek, dark mode dashboard UI mock with an animated shield logo

### 🗣️ Presenter Script
> *"Good day, everyone. Today, I am proud to present **CyberBoyAI**, a next-generation, multi-agent cybersecurity orchestrator built to defend modern digital workflows against phishing, malware, and social engineering. CyberBoyAI isn't just another security wrapper. It is a live, production-grade, 9-layer defense-in-depth platform currently running in Docker on Render, with a modern Next.js single-page dashboard live on Vercel. Today, I will walk you through the math, the machine learning, and the defensive engineering that makes this platform elite."*

---

## Slide 2: The Core Problem: Why Modern Blacklists Fail
### 🖥️ Slide Content
*   **The Status Quo:** Traditional firewalls and antivirus tools rely strictly on **Blacklists** (lists of known bad domains).
*   **The Critical Vulnerability:** 
    *   Scammers buy brand-new domains for $0.99 and register them minutes before an attack.
    *   These are called **Zero-Day Threats**. They are mathematically absent from all global databases.
    *   **Database Sync Delay:** Commercial blacklists take hours or days to sync. An attack is often over before the database is updated.
*   **The CyberBoyAI Philosophy:** *Assume the database is always outdated.* Interrogate the URL's structural DNA, test it live in a sandbox, and use AI to evaluate the page visual structure in real time.

### 🗣️ Presenter Script
> *"To understand why CyberBoyAI is necessary, we must understand the failure of modern cybersecurity. 99% of current email and web filters rely on 'Blacklists'—essentially a massive dictionary of known bad links. But here is the catch: hackers buy cheap top-level domains for under a dollar and launch their attacks instantly. This creates a 'Zero-Day' gap. By the time a security firm detects the link, registers it, and syncs their database, the damage is already done. CyberBoyAI operates on a Zero-Trust philosophy: we assume all external links are hostile, and we actively dissect their physical, structural, and behavioral properties in real time rather than just looking them up."*

---

## Slide 3: The Technology Stack & Production Architecture
### 🖥️ Slide Content
```
 ┌────────────────────────────────────────────────────────┐
 │            Vercel (Next.js 14 / TypeScript)           │
 └───────────────────────────┬────────────────────────────┘
                             │ HTTPS API Calls
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │           Render (FastAPI / Docker Container)          │
 └───────┬───────────────────┬────────────────────┬───────┘
         │                   │                    │
         ▼                   ▼                    ▼
 ┌───────────────┐   ┌───────────────┐   ┌────────────────┐
 │ Supabase DB   │   │ OpenAI API    │   │ Live OSINT     │
 │ (PostgreSQL)  │   │ (GPT-4o Mini) │   │ (GSB/AbuseIP)  │
 └───────────────┘   └───────────────┘   └────────────────┘
```
*   **Frontend:** Next.js 14, React, Tailwind CSS, Lucide Icons, LocalStorage caching.
*   **Backend Engine:** Python, FastAPI, AsyncIO (high-concurrency, non-blocking requests).
*   **Data Tier:** Supabase PostgreSQL (Periodic scheduler cache, community reports).
*   **AI & Scraper:** OpenAI GPT-4o-mini & GPT-4o-Vision, Playwright (Headless Chromium).
*   **Machine Learning (Multi-Class Classification):** Scikit-Learn (Random Forest Models mapping URLs to four classes: `benign`, `phishing`, `malware`, and `defacement`).

### 🗣️ Presenter Script
> *"Here is how CyberBoyAI is built. The user interacts with a premium, high-speed Next.js React frontend hosted on Vercel. When a threat is submitted, it securely pings a Dockerized FastAPI Python backend deployed on Render. Under the hood, the backend runs asynchronous pipelines using Python's AsyncIO, querying our Supabase database, calling live OSINT feeds, running our custom machine learning models, and spawning Playwright headless browsers to scrape target pages—all in parallel in under 3 seconds. The machine learning agent uses a highly-tuned multi-class classification model, identifying not just phishing, but malware and defacement attacks as well."*

---

## Slide 4: The 9-Layer Defense-in-Depth Pipeline
### 🖥️ Slide Content
*   **Layer 1: Multimodal Input (Vision OCR):** Scans submitted screenshots/images, decodes QR codes ("Qishing").
*   **Layer 2: Linguistic NLP Engine:** Analyzes SMS/Email phrasing for social engineering threats.
*   **Layer 3: URL Redirect Unshortener:** Recursively follows redirects (e.g., `bit.ly` hops) to find true endpoints.
*   **Layer 4: Fuzzy Brand Protection:** Brand typosquatting and homoglyph detection (Levenshtein).
*   **Layer 5: OSINT Blacklist Intelligence:** Multi-source lookup (Safe Browsing, URLhaus, OpenPhish, AbuseIPDB, OTX).
*   **Layer 6: Structural DNA Agent:** Random Forest analysis of 20 structural features of the URL.
*   **Layer 7: Playwright Behavioral Sandbox:** Safely visits and inspects live page behaviors without executing JS.
*   **Layer 8: OpenAI DOM Forensic Analysis:** Inspects the raw visual and text structure of the page for phishing kits.
*   **Layer 9: Path-Aware Whitelisting:** Prevents cloud abuse (trusted domains hosting deep-path malicious forms).

### 🗣️ Presenter Script
> *"Rather than relying on one technique, CyberBoyAI routes every input through a massive gauntlet of 9 distinct layers. We start by unravelling images and QR codes using vision models. We follow shortener chains, analyze brand typosquatting, check global databases, run local machine learning, spin up a secure Playwright chromium browser to safely scrape the page, run generative AI DOM forensic models, and filter out cloud abuse before compiling the final result. If a hacker manages to bypass three of these layers, they will still get caught by the remaining six."*

---

## Slide 5: Input Analysis: Vision OCR, Redirect Chains & Email Processing
### 🖥️ Slide Content
*   **Visual Phishing (OCR & QR Decoding):**
    *   GPT-4o-Vision extracts links from visual QR codes ("Qishing") and screens visual text to bypass traditional filters.
*   **Email Processing Pipeline:**
    *   Unified training corpus merging **Apache SpamAssassin Corpus** with **Zenodo SpamAssassin CSV**.
    *   Parses raw `.eml` headers, decodes text/plain MIME payloads, scrubs code formatting, and deduplicates to guarantee semantic training data.
*   **Redirect Tracker:**
    *   Recursively follows redirect chains (up to 10 hops) to unmask target landing pages hidden behind shorteners (e.g., `bit.ly`).

### 🗣️ Presenter Script
> *"Let's talk about our entry-level analysis pipelines. Attackers frequently hide links inside visual QR codes in emails, a technique known as 'Qishing'. CyberBoyAI immediately runs optical character recognition and QR decoding using vision AI to extract the true text. If the input is an email, our system parses raw email headers and decodes plain text segments from a unified training corpus made from the Apache SpamAssassin and Zenodo datasets. Furthermore, if a link is hidden behind a shortener like bit.ly, our recursive Redirect Tracker follows up to 10 redirects until it exposes the final true destination."*

---

## Slide 6: The Mathematical Engine: Core Algorithms & Heuristics
### 🖥️ Slide Content
*   **1. Shannon Entropy (Domain Character Randomness):**
    *   *What it does:* Measures the information density/randomness of characters in a domain. Detects auto-generated domains and botnet Domain Generation Algorithms (DGA).
*   **2. Normalized Levenshtein Distance (Fuzzy Brand Matching):**
    *   *What it does:* Calculates the minimum character edits required to transform a subdomain into a protected global brand. Identifies typosquatting visual substitutions (e.g., `netfl1x`).
*   **3. TF-IDF Vectorization (NLP Semantic Encoding):**
    *   *What it does:* Converts raw text bodies into high-dimensional numerical vectors, mathematically suppressing neutral words ("the," "and") and amplifying rare scam keywords ("suspended," "bvn").
*   **4. Gini Impurity (ML Tree-Splitting Optimization):**
    *   *What it does:* Split optimizer during machine learning training that maximizes the statistical separation between clean and malicious data, constructing optimal decision trees.
*   **5. Consensus-Aware Weighted Fusion (Dynamic Score Aggregation):**
    *   *What it does:* An adaptive weighted sum that aggregates our 9 layers, shifting weights to let dynamic visual AI analysis override static structural scores in conflict zones.

### 🗣️ Presenter Script
> *"Rather than using complex formulas that are hard to audit, CyberBoyAI operates on 5 highly robust, explainable mathematical concepts. We use Shannon Entropy to measure character randomness and catch auto-generated domains. We run Levenshtein Distance fuzzy matching to detect typosquatting of global brands. We use TF-IDF vectorization to convert English emails into mathematical matrices, amplifying rare threat words. During training, we use Gini Impurity to split our machine learning trees. Finally, we use Consensus-Aware Weighted Fusion to dynamically adjust weights when agents disagree, letting high-confidence visual AI checks override static URL structures. This mathematical combination makes our system incredibly stable and explainable."*

---

## Slide 7: OSINT Intelligence & URL Dataset Pipeline
### 🖥️ Slide Content
*   **Live OSINT & Caching:**
    *   Queries **Google Safe Browsing** (Live API), **AbuseIPDB** (IP Reputation), and **AlienVault OTX** (Threat Pulse Counts) in parallel.
    *   Synchronizes bulk threat feeds (OpenPhish, URLhaus) daily into a local Supabase PostgreSQL database.
*   **URL ML Model Dataset:**
    *   Trained on the highly respected Kaggle dataset: **`sid321axn/malicious-urls-dataset`**.
    *   Contains hundreds of thousands of records spanning 4 classes (`benign`, `phishing`, `malware`, `defacement`).
*   **High-Speed Feature Extraction:**
    *   Features extracted in parallel using Python's **`ProcessPoolExecutor`** running chunked batches of **50,000 URLs** simultaneously to maximize multi-core CPU efficiency.

### 🗣️ Presenter Script
> *"To ensure our intelligence is authoritative, we query live global databases like Google Safe Browsing and AbuseIPDB in parallel. To guarantee speeds under 3 seconds without getting rate-limited, we sync bulk intelligence from OpenPhish and URLhaus daily into our local Supabase instance. For our URL Machine Learning model, we trained on the industry-standard Kaggle Malicious URLs dataset containing hundreds of thousands of active threats. To make the pipeline production-ready, we developed a high-speed parallel preprocessing pipeline using Python's ProcessPoolExecutor, which chunks the URLs into batches of 50,000 and extracts features across all CPU cores in parallel. This represents extreme, enterprise-level preprocessing speed."*

---

## Slide 8: Random Forest URL Classifier: Exact Specifications
### 🖥️ Slide Content
*   **Exact Model Hyperparameters:**
    *   Algorithm: `RandomForestClassifier` (Scikit-Learn).
    *   Trees ($T$): **200 estimators** with a `max_depth` limit of **15** (prevents overfitting) and `min_samples_leaf=2`.
    *   Split: **80% Training, 20% Evaluation** (seed `random_state=42`).
*   **URL Features Extracted (20 Core Features):**
    *   *Lexical:* `domain_age_days`, `keyword_count`, `entropy`, `subdomain_depth`, `url_length`, `hyphen_count`, `special_char_count`, `path_depth`, `percent_encoding_count`.
    *   *Technical:* `is_https`, `tld_risk_score`, `numeric_substitution`, `double_slash_redirect`, `is_ip_address`, `v_c_ratio`, `consecutive_chars`, `is_shortened`, `has_non_standard_port`, `has_suspicious_extension`, `suspicious_subdomain`.

### 🗣️ Presenter Script
> *"Here are the exact machine learning engineering details. We configured our Random Forest URL model with 200 estimator trees, capping the maximum depth to 15. This depth limit is critical to prevent overfitting on the training data. We split the data strictly into 80% training and 20% validation. When a URL is scanned, our backend extracts exactly 20 core mathematical features, including lexical indicators like subdomain depth and path depth, as well as technical anomalies like non-standard ports or suspicious file extensions. The forest processes these 20 vectors, voting to yield a final threat class probability."*

---

## Slide 9: Playwright Sandbox & OpenAI Forensics
### 🖥️ Slide Content
*   **Playwright Headless Chrome Sandbox:**
    *   Visits the target URL dynamically with **`java_script_enabled=False`** for ultimate safety against drive-by malware.
    *   Inspects HTTP headers, follows redirects, extracts form inputs, and retrieves raw page text.
*   **OpenAI DOM Forensic Analysis:**
    *   Scrubbed HTML is parsed by our `OpenAIAgent` using **GPT-4o-mini**.
    *   Inspects the actual visual content and credential forms.
    *   Extracts identified brands, official domains, and assigns an AI threat score.
    *   **Dynamic Anti-Jailbreak Boundaries:** Wraps target HTML in randomized UUID boundaries (`BOUNDARY_{UUID}_START`) to prevent prompt injection.

### 🗣️ Presenter Script
> *"If a zero-day link doesn't match any database, CyberBoyAI moves to our behavioral layers. We launch a headless, sandboxed Chromium browser via Playwright. We explicitly disable JavaScript. This is a vital security control: it means no malicious exploit can run on our server. Playwright scrapes the raw HTML text and counts the security forms. This clean text is passed to our OpenAI Forensic Agent. The AI acts like an expert analyst, reviewing the text for credential harvesting patterns and returning an AI risk score. To prevent hackers from jailbreaking the AI, we wrap all scraped web code in a randomized UUID boundary, telling the AI that everything inside is hostile."*

---

## Slide 10: Path-Aware Whitelisting (Cloud Abuse Defense)
### 🖥️ Slide Content
*   **The Threat (Cloud Abuse):**
    *   Attackers host phishing forms on legitimate cloud infrastructure (Google Forms, Microsoft Forms, Notion, GitHub Pages).
    *   Standard whitelists see `google.com` and automatically say "SAFE," letting the attack slide through.
*   **CyberBoyAI Path-Aware Protection:**
    *   Recognizes globally trusted base domains (`google.com`, `github.io`).
    *   **The Rule:** A fast-path "SAFE" bypass is granted **only** if the domain is a bare domain or trusted path (e.g., Google Search).
    *   If a deep user-generated path is detected (e.g., `docs.google.com/forms/d/xyz`), **the whitelist is stripped** and the system forces full Lookup, ML, and Playwright scans on the path.

### 🗣️ Presenter Script
> *"Cloud Abuse is one of the hardest threats for modern enterprise filters to block. Scammers host their phishing pages on Google Forms or Microsoft Forms. Because those domains belong to Google or Microsoft, traditional systems blindly trust them. CyberBoyAI implements Path-Aware Whitelisting. If you visit a search page on Google, it gets bypassed instantly. But if you visit a deep user path like Google Forms, the whitelist is immediately stripped, and our system executes a full database, machine learning, and visual AI scan on that specific path. This blocks cloud abuse completely."*

---

## Slide 11: Local ML Risk vs. Global Confidence
### 🖥️ Slide Content
*   **Local ML Risk:**
    *   Measures the physical shape of the link.
    *   **"Classified as Phishing (97% risk)"** means the URL structure matches 97% of standard malicious strings.
*   **Global Confidence Score ($C$):**
    *   Aggregates all 9 layers. Evaluated on distance to absolute state:
    $$C = \begin{cases}
      S_{\text{final}} \times 100 & \text{if Verdict is DANGEROUS or SUSPICIOUS}, \\
      (1.0 - S_{\text{final}}) \times 100 & \text{if Verdict is SAFE.}
    \end{cases}$$
*   **The Stalemate State (Disagreement):**
    *   If a link has a random structure (95% ML Risk) but is a legitimate URL shortener (0% brand risk, 0% AI risk), the engine assigns a **Stalemate Score** ($\sim 0.50$), rendering as **"SUSPICIOUS"** with **$50\%$ Confidence**.

### 🗣️ Presenter Script
> *"In our UI, you will occasionally notice that the ML Risk score says 98%, but the Global Confidence says 50%. This is not an error; it is a feature called Consensus Conflict Resolution. For example, a link shortener like 'bit.ly' has a random mathematical structure, so the ML Agent flags it as high risk. However, our database and visual AI agents see that it is a legitimate service. The engine resolves this stalemate by assigning a Suspicious verdict with 50% confidence. This tells the user: 'One part of our engine is suspicious, but we don't have enough collective proof to block it.' This drastically reduces false positives while keeping the user guarded."*

---

## Slide 12: Key Defense Edge Cases & FAQ
### 🖥️ Slide Content
*   **"What if the website is currently offline?"**
    *   *Defense:* Playwright detects status codes ($0, 404, 403$). The system bypasses OpenAI API calls entirely to save API costs and returns a "Host Unreachable" warning.
*   **"What if a hacker hides a link inside a visual button in an email?"**
    *   *Defense:* Our Chrome Extension runs **Deep DOM Extraction** which scrapes raw webmail HTML, follows hidden anchors, and pulls all `href` links for scanning.
*   **"What if a hacker attempts to spoof the sender address?"**
    *   *Defense:* The `EmailAgent` parses raw SMTP headers. If the `From` field and `Reply-To` domains do not align, a severe spoofing penalty is added.

### 🗣️ Presenter Script
> *"When designing CyberBoyAI, we accounted for advanced edge cases. If a target site goes offline, we immediately detect the HTTP status and abort OpenAI calls to save API tokens. If a hacker hides a link inside a 'Click Here' button, our Chrome extension injects scripts directly into the DOM of your inbox, extracting the hidden href links behind the buttons. If a scammer attempts to spoof email domains, we analyze raw SMTP headers and penalize the score if the From and Reply-To addresses disagree. Every loophole has been shut."*

---

## Slide 13: Future Work: Scaling to Enterprise Grade
### 🖥️ Slide Content
*   **1. Residential Proxy Integration (Anti-Cloaking):**
    *   *Upgrade:* Route Playwright chromium traffic through rotating residential ASNs (using our pre-configured `ProxyRotationManager`) to bypass adversary IP blocklists.
*   **2. Closed-Loop Machine Learning (Active Learning):**
    *   *Upgrade:* Automate monthly model retraining pipelines. Pull community reports from Supabase, retrain `model.joblib`, and redeploy with zero downtime.
*   **3. Automated CAPTCHA / Turnstile Solving:**
    *   *Upgrade:* Integrate visual AI solvers to bypass Cloudflare challenge pages and scan deep forms hidden behind gateway gates.
*   **4. Decentralized Databases:**
    *   *Upgrade:* Sync threat caches to a decentralized distributed ledger to guarantee cross-enterprise high availability.

### 🗣️ Presenter Script
> *"To scale CyberBoyAI into a commercial enterprise product, our future roadmap focuses on defeating sophisticated adversary evasion. First, we will activate our pre-configured Residential Proxy manager to rotate scans through home internet connections, completely bypassing adversary blocklists. Second, we will build a closed-loop active learning pipeline that automatically pulls daily user-reported threats from Supabase, retrains our machine learning classifiers, and redeploys our models with zero downtime. Finally, we will integrate automated CAPTCHA solvers to bypass Cloudflare gates. This will elevate CyberBoyAI from a high-quality platform to an unbeatable enterprise shield."*

---

## Slide 14: Summary of Achievements
### 🖥️ Slide Content
*   **Live End-to-End Production:** Dockerized FastAPI on Render, React/Next.js dashboard on Vercel, Supabase PostgreSQL cloud tier.
*   **9-Layer Security Architecture:** Consensus-aware weighted engine, vision OCR, linguistic NLP, and Sandboxed dynamic browsers.
*   **Elite Zero-Day Defense:** Multi-feature URL Random Forest classifier and custom AI DOM inspector.
*   **Clean & High-Speed:** Client-side Next.js configuration completely bypassing file tracing for ultra-fast load and build speeds.
*   **Interactive History:** Real-time clickable history feed reading from active backend caching pools.

### 🗣️ Presenter Script
> *"In summary, we have built and deployed a production-grade, 9-layer threat detection pipeline. It combines the speed of local databases, the mathematical rigor of machine learning, and the visual reasoning of generative AI into a unified, secure system. It is fully live on the web, fully synchronized, and ready to protect users. Thank you for your time, and I am now open to any questions you may have."*

---
---

# PART 2: COMPREHENSIVE ARCHITECTURAL REFERENCE

This section serves as your offline reference manual. It contains the complete technical details of the codebase, models, and databases.

## 1. Directory Structure Reference
```
cyberboyAI/
├── ARCHITECTURE.md                  # Detailed 9-layer overview
├── Dockerfile                       # Production container specs
├── PRESENTATION_GUIDE.md            # Visual overview guide
├── MASTER_PRESENTATION_GUIDE.md     # THIS FILE (Master Blueprint)
│
├── backend/                         # FastAPI Engine
│   ├── main.py                      # Server Entrypoint & Lifespan
│   ├── scheduler.py                 # OpenPhish Daily Cron Tasks
│   ├── requirements.txt             # Python Dependencies
│   │
│   ├── agents/                      # Multi-Agent Cluster
│   │   ├── brand_agent.py           # Typosquatting Analysis
│   │   ├── lookup_agent.py          # OSINT Blacklist Engine
│   │   ├── ml_agent.py              # URL Structural DNA Classifiers
│   │   ├── email_agent.py           # SMS/Email Linguistic NLP
│   │   ├── openai_agent.py          # Playwright Scraper & AI DOM
│   │   └── verdict.py               # Consensus Weighted Fusion
│   │
│   ├── tools/                       # Utilities & Tools
│   │   ├── proxy_manager.py         # Residential Proxy Rotation
│   │   ├── safe_browsing.py         # Google Safe Browsing API
│   │   ├── supabase_client.py       # Cloud DB ORM Connection
│   │   └── rules_engine.py          # Heuristic Phishing Kit Finder
│   │
│   └── docs/                        # Sub-documentation
│       ├── scoring_architecture.md  # Local vs Global Scores
│       └── mathematical_foundations.md # Math & Formulas
│
└── frontend/                        # Next.js React Dashboard
    ├── next.config.mjs              # Disabled tracing config
    ├── app/                         # App Router
    │   ├── page.tsx                 # Home View & Clickable History
    │   └── layout.tsx               # Main Layout View
    ├── components/                  # Premium UI components
    │   ├── ChatInput.tsx            # Chat Entry Field
    │   ├── ChatBubble.tsx           # Dialogue Bubbles
    │   └── RiskGauge.tsx            # Radial Risk UI
    └── lib/
        └── api.ts                   # Fetch API hooks
```

## 2. Supabase PostgreSQL Schema (`phishtank_cache`)
The daily threat feeds are synchronized into a PostgreSQL table designed for high-speed indexing:

```sql
CREATE TABLE phishtank_cache (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    threat_type VARCHAR(50) DEFAULT 'phishing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Crucial High-Speed Indexing for URL queries
CREATE INDEX idx_phishtank_url ON phishtank_cache(url);
```

## 3. Playwright Sandboxing Core Implementation
Inside `backend/agents/openai_agent.py`, the Playwright chromium instance is launched under strict security settings:

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
        java_script_enabled=False, # Absolute protection against JS drive-by malware
        proxy=proxy_manager.get_playwright_proxy() # Rotating proxy hook
    )
    page = context.new_page()
    response = page.goto(url, timeout=15000, wait_until="domcontentloaded")
```

## 4. Anti-Jailbreak Wrapper Implementation
Inside `backend/agents/openai_agent.py`, text parsed from Playwright is wrapped inside randomized boundaries to neutralize prompt injections:

```python
boundary = f"BOUNDARY_{uuid.uuid4().hex.upper()}"
sanitized_text = raw_text.replace("<<<", "").replace(">>>", "")

context = f"""URL: {url}
Site Status: {status}
Title: {title}
Forms: {forms}

{boundary}_START
{sanitized_text}
{boundary}_END
"""
```
The system instructions explicitly instruct the model that everything residing between `{boundary}_START` and `{boundary}_END` is untrusted data and must not be parsed as instructions.
