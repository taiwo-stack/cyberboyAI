# GaudOn — Mathematical Foundations & Logic Models

This document serves as the formal mathematical specification of the threat detection pipelines running in the **GaudOn** engine. It outlines every equation, logic model, algorithmic optimization, and security proof used to compute threat scores, identify brand impersonation, perform linguistic forensics, and maintain consensus.

---

## 1. Shannon Entropy ($H$)
### Concept: Domain Obfuscation & Algorithmic Domain Generation (DGA)
In information theory, **Shannon Entropy** measures the level of "uncertainty" or randomness in a set of outcomes. Phishing attackers frequently use Domain Generation Algorithms (DGA) or highly randomized strings (e.g., `x89q10a-verification.cyou`) to bypass standard name filters and dynamically rotate servers.

We use Shannon Entropy to mathematically analyze the character distribution of the domain string.

### Mathematical Equation
For a domain string $X$ containing characters $x_1, x_2, \dots, x_n$ with a unique vocabulary of symbols $V$:

$$H(X) = - \sum_{i=1}^{|V|} P(x_i) \log_2 P(x_i)$$

Where:
*   $P(x_i) = \frac{f(x_i)}{L}$ is the empirical probability of character $x_i$ appearing in the string.
*   $f(x_i)$ is the absolute frequency of character $x_i$.
*   $L$ is the total length of the domain string.
*   $\log_2$ represents the binary logarithm (bits of information per character).

### Interpretation Scale
*   **$H(X) < 3.0$**: Highly structured and redundant (e.g., `google.com` or `apple.com`). Extremely low probability of randomized DGA.
*   **$3.0 \le H(X) \le 4.2$**: Standard linguistic domain (e.g., `cyberboy-security-portal.org`).
*   **$H(X) > 4.5$**: High-entropy chaos (e.g., `a7d8f921bc90a.net`). Triggers the **High-Entropy Anomalous Domain** flag in the MLAgent, heavily boosting the structural risk probability.

---

## 2. Normalized Levenshtein Distance ($\text{Sim}_{\text{Brand}}$)
### Concept: Brand Impersonation & Typosquatting
To capture brands being impersonated using visual tricks (e.g., `netfl1x` instead of `netflix`, `paypaI` with a capital `I` instead of `paypal`), the `BrandAgent` calculates the **Levenshtein Distance** (minimum edit distance) between the extracted URL components and a list of globally protected brands.

### Mathematical Equation
The raw Levenshtein distance between two strings $s_1$ and $s_2$ of lengths $|s_1|$ and $|s_2|$ is calculated recursively as:

$$\text{lev}_{s_1, s_2}(i, j) = \begin{cases}
  \max(i, j) & \text{if } \min(i, j) = 0, \\
  \min \begin{cases}
          \text{lev}_{s_1, s_2}(i-1, j) + 1 \\
          \text{lev}_{s_1, s_2}(i, j-1) + 1 \\
          \text{lev}_{s_1, s_2}(i-1, j-1) + \text{cost}
       \end{cases} & \text{otherwise.}
\end{cases}$$

Where:
*   $\text{cost} = 0$ if $s_1[i] = s_2[j]$, and $1$ otherwise.
*   The three operations minimized represent **Deletion**, **Insertion**, and **Substitution** respectively.

To turn this distance into a standard $0.0 \dots 1.0$ similarity score, we **normalize** the metric against the length of the longer string:

$$\text{Sim}_{\text{Brand}}(s_1, s_2) = 1 - \frac{\text{lev}(s_1, s_2)}{\max(|s_1|, |s_2|)}$$

### Brand Impersonation Thresholds & Leet Penalties
When evaluating subdomains or subcomponents, a penalty factor $\gamma = 0.94$ is applied to account for structural noise:

$$\text{Sim}_{\text{Final}} = \text{Sim}_{\text{Brand}} \times \gamma$$

*   **$\text{Sim}_{\text{Final}} \ge 0.90$**: **Definitive Impersonation**. Triggers **Fast-Path Override 2** (forces Verdict to `DANGEROUS` with a $0.97$ confidence score).
*   **$0.75 \le \text{Sim}_{\text{Final}} < 0.90$**: **High-Probability Typosquatting**. Triggers active similarity boosts in the Verdict Engine.
*   **$\text{Sim}_{\text{Final}} < 0.75$**: Safe/Unrelated.

---

## 3. TF-IDF (Linguistic Feature Extraction)
### Concept: Email Phishing NLP Forensics
The `EmailAgent` parses the linguistic text of forwarded emails or message bodies to spot urgent psychological manipulation (e.g., "immediate suspension," "security breach," "update bank details"). To convert raw text into a mathematical vector before sending it to the Random Forest model, we use **Term Frequency-Inverse Document Frequency (TF-IDF)**.

### Mathematical Equations

#### 1. Term Frequency ($\text{TF}$)
Measures how frequently a term $t$ occurs in a specific document $d$:

$$\text{TF}(t, d) = \frac{f_{t,d}}{\sum_{t' \in d} f_{t',d}}$$

Where $f_{t,d}$ is the raw count of term $t$ in document $d$.

#### 2. Inverse Document Frequency ($\text{IDF}$)
Measures how rare or common a term is across the entire corpus $D$ of training emails. Common terms like "the" get suppressed, while rare threat terms like "verify-bvn" or "crypto-wallet" get amplified:

$$\text{IDF}(t, D) = \log \left( \frac{1 + |D|}{1 + |\{d \in D : t \in d\}|} \right) + 1$$

#### 3. Fused TF-IDF Vector
The final numerical weight of term $t$ in document $d$ is:

$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$

This generates an $N$-dimensional vector for every email, capturing the exact semantic threat profile of the text.

---

## 4. Random Forest Classification (Ensemble Learning)
### Concept: Machine Learning Threat Classification
Both the **MLAgent** (for URL structures) and the **EmailAgent** (for NLP text) utilize a **Random Forest Classifier** ($M$ Decision Trees) to generate risk probabilities.

### Mathematical Split Criterion: Gini Impurity ($I_G$)
During training, the decision trees split nodes by choosing features that minimize the Gini Impurity (making the split groups as "purely clean" or "purely malicious" as possible).

For a node containing samples from $J$ classes, the Gini Impurity $I_G(p)$ is defined as:

$$I_G(p) = 1 - \sum_{i=1}^{J} p_i^2$$

Where $p_i$ is the probability of a sample belonging to class $i$ at that node.

### Probability Ensemble Voting
At runtime, the Random Forest does not output a simple binary "yes/no". It aggregates the individual probability distributions of $T$ independent trees to compute a smooth, continuous risk score $P(y = \text{phishing} | x)$:

$$P(y = c \mid x) = \frac{1}{T} \sum_{t=1}^{T} P_t(y = c \mid x)$$

Where $P_t(y = c \mid x)$ is the probability predicted by the $t$-th individual decision tree. This probability maps directly to the local agent's score.

---

## 5. Consensus-Aware Weighted Verdict Fusion
### Concept: The Multi-Agent Verdict Engine
The central engine (`verdict.py`) takes the scores from all active agents and computes a single unified verdict. To prevent one agent from dominating, the engine uses **Dynamically Shifting Multivariate Weighted Fusion**.

### General Equation
The basic fused threat score $S_{\text{final}}$ is defined as:

$$S_{\text{final}} = \sum_{i \in \text{Agents}} w_i \cdot S_i + \text{Boosts}$$

Subject to:

$$\sum_{i \in \text{Agents}} w_i = 1.0$$

Where $S_i$ represents the local agent scores, and $w_i$ represents their relative weights.

### Adaptive Weight Configurations
The system detects **Consensus Stalemate** (when agents disagree) and shifts weights adaptively:

```
                  ┌─────────────────────────────────┐
                  │ Calculate Score Gap             │
                  │   Δ = |S_ML - S_AI|             │
                  └────────────────┬────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │      Is Δ ≤ 0.30 (Agreement)?   │
                  └──────┬────────────────────┬─────┘
                         │ Yes                │ No
                         ▼                    ▼
             ┌──────────────────────┐  ┌──────────────────────────────┐
             │   Standard Weights   │  │   Who is higher: ML or AI?   │
             │ w_lookup = 0.35      │  └──────┬────────────────┬──────┘
             │ w_ML     = 0.30      │         │                │
             │ w_AI     = 0.20      │         ▼ ML > AI        ▼ AI > ML
             │ w_behav  = 0.15      │  ┌──────────────┐ ┌─────────────────────┐
             └──────────────────────┘  │ AI visited.  │ │ AI detected visual  │
                                       │ Is it confident│ credentials.        │
                                       │ & flag-free? │ │ Give AI maximum weight│
                                       └──┬────────┬──┘ └─────────────────────┘
                                      Yes │        │ No
                                          ▼        ▼
                                   ┌──────────┐ ┌──────────┐
                                   │AI weight │ │ML weight │
                                   │  boosted │ │  boosted │
                                   └──────────┘ └──────────┘
```

#### 1. Agreement Zone ($|S_{\text{ML}} - S_{\text{AI}}| \le 0.30$)
The standard baseline weights balance speed and depth:
*   $w_{\text{lookup}} = 0.35$ (Blacklists & Intel)
*   $w_{\text{ML}} = 0.30$ (URL Structural DNA)
*   $w_{\text{AI}} = 0.20$ (LLM Scrape Reasoning)
*   $w_{\text{behavior}} = 0.15$ (SSL, Cloaking, Redirects)

#### 2. Conflict: ML is High, AI is Low ($S_{\text{ML}} > S_{\text{AI}}$)
Because the AI (OpenAI) successfully rendered and inspected the DOM, its clean verdict is highly trusted *if* the AI is confident ($C_{\text{AI}} \ge 65$) and observed no malicious forms:
*   Weights shift to: $w_{\text{lookup}} = 0.35$, **$w_{\text{ML}} = 0.20$**, **$w_{\text{AI}} = 0.30$**, $w_{\text{behavior}} = 0.15$

#### 3. Conflict: AI is High, ML is Low ($S_{\text{AI}} > S_{\text{ML}}$)
This is the most critical conflict. If the URL structure looks completely innocent, but the AI discovered a credential-harvesting form, the AI's real-time visual assessment override is activated:
*   Weights shift to: $w_{\text{lookup}} = 0.30$, **$w_{\text{ML}} = 0.15$**, **$w_{\text{AI}} = 0.40$**, $w_{\text{behavior}} = 0.15$

#### 4. DNS Offline / Unreachable ($S_{\text{status}} = 0$)
Since there is no live website to scan, the AI and behavioral weights are minimized, transferring weight to the structural ML parser:
*   Weights shift to: $w_{\text{lookup}} = 0.10$, **$w_{\text{ML}} = 0.45$**, $w_{\text{AI}} = 0.35$, $w_{\text{behavior}} = 0.10$

---

## 6. Global System Confidence Score ($C$)
### Concept: UI Metric Translation
The "Confidence" score rendered in the frontend gauge represents the **absolute probability distance** to a definitive state ($0\%$ risk or $100\%$ risk). 

### Mathematical Equation

$$C = \begin{cases}
  S_{\text{final}} \times 100 & \text{if Verdict is DANGEROUS or SUSPICIOUS}, \\
  (1.0 - S_{\text{final}}) \times 100 & \text{if Verdict is SAFE.}
\end{cases}$$

This means:
*   If $S_{\text{final}} = 0.98$ (DANGEROUS), the gauge renders **98% Confidence** of threat presence.
*   If $S_{\text{final}} = 0.02$ (SAFE), the gauge renders **98% Confidence** of threat absence.

---

## 7. Fast-Path Logic Overrides
Before running the weighted equations, the engine checks two **Fast-Path** boundary conditions representing absolute logical truths:

### Fast-Path 1: Verified Blacklist
$$\text{If } \text{Lookup}_{\text{matched}} = \text{True} \land S_{\text{lookup}} \ge 0.95 \implies \begin{cases} \text{Verdict} = \text{"DANGEROUS"} \\ S_{\text{final}} = 1.0 \end{cases}$$

### Fast-Path 2: Near-Perfect Impersonation
$$\text{If } \text{Brand}_{\text{is\_impersonation}} = \text{True} \land \text{Sim}_{\text{Brand}} \ge 0.90 \implies \begin{cases} \text{Verdict} = \text{"DANGEROUS"} \\ S_{\text{final}} = 0.97 \end{cases}$$
