"""
brand_agent.py — Global Brand Impersonation Detector (v2)

Three-layer detection:
  Layer 1: Tranco Top 500 global domains — Levenshtein fuzzy matching
  Layer 2: Homoglyph normalization — catches visually deceptive Unicode tricks
  Layer 3: Leet-speak normalization — catches numeric substitutions (4→a, 0→o, etc.)
"""

import tldextract
import Levenshtein
from typing import List, Optional
from schemas.agent_outputs import BrandAgentResult
from tools.global_brands import global_brand_manager

# ── Homoglyph Map ─────────────────────────────────────────────────────────────
# Visually deceptive characters that look identical in most fonts.
# Attackers use these to register domains that appear legitimate to the human eye.
_HOMOGLYPH_MAP = str.maketrans({
    # Latin lookalikes
    "ı": "i",   # Turkish dotless i
    "ο": "o",   # Greek omicron
    "а": "a",   # Cyrillic a
    "е": "e",   # Cyrillic e
    "р": "p",   # Cyrillic p
    "с": "c",   # Cyrillic c
    "х": "x",   # Cyrillic x
    # Multi-char tricks handled separately below
})

# Multi-character homoglyphs (sequence → replacement)
_MULTI_HOMOGLYPHS = [
    ("rn", "m"),    # rn looks like m in most fonts
    ("vv", "w"),    # vv looks like w
    ("cl", "d"),    # cl looks like d
    ("li", "h"),    # li can look like h
]

# ── Leet-speak Map ────────────────────────────────────────────────────────────
def _normalize_leet(s: str) -> str:
    return (s
        .replace("0", "o").replace("1", "l").replace("3", "e")
        .replace("4", "a").replace("5", "s").replace("7", "t")
        .replace("@", "a").replace("$", "s").replace("!", "i")
    )

def _normalize_homoglyphs(s: str) -> str:
    """Applies single-char and multi-char homoglyph substitutions."""
    s = s.translate(_HOMOGLYPH_MAP)
    for seq, replacement in _MULTI_HOMOGLYPHS:
        s = s.replace(seq, replacement)
    return s

def _normalize_full(s: str) -> str:
    """Applies both leet-speak and homoglyph normalization."""
    return _normalize_leet(_normalize_homoglyphs(s))


class BrandAgent:
    def __init__(self):
        """Initializes the Brand Agent and triggers the global brand list load."""
        # Trigger the Tranco Top 500 load (runs in background thread if needed)
        global_brand_manager.load()

    async def check(self, url: str) -> BrandAgentResult:
        """
        Checks if a URL is impersonating a globally known brand using
        three normalization passes + Levenshtein distance.
        """
        try:
            ext = tldextract.extract(url)
            submitted_label = ext.domain.lower()           # e.g. "paypa1-secure"
            submitted_domain = ext.registered_domain.lower()  # e.g. "paypa1-secure.xyz"

            if not submitted_label:
                return BrandAgentResult(is_impersonation=False, similarity_score=0.0)

            # Get current global brand labels (auto-refreshes if stale)
            brand_labels = global_brand_manager.get_brands()

            # Pre-compute all three normalized forms of the submitted label
            label_leet       = _normalize_leet(submitted_label)
            label_homoglyph  = _normalize_homoglyphs(submitted_label)
            label_full       = _normalize_full(submitted_label)
            # Strip hyphens/underscores for compound domain checks
            label_stripped   = label_full.replace("-", "").replace("_", "")

            # Split by hyphen — attackers add suffixes like -billing, -secure, -verify
            # e.g. "netfl1x-billing" → ["netfl1x", "billing"]
            # We check each component individually so "netfl1x" is compared vs "netflix"
            label_components = [
                _normalize_full(part)
                for part in submitted_label.split("-")
                if len(part) >= 3  # Skip trivially short parts
            ]

            highest_similarity = 0.0
            closest_brand_label = None

            for known_label in brand_labels:
                known_label = known_label.lower()
                if len(known_label) < 3:
                    continue  # Skip trivially short labels

                max_len = max(len(submitted_label), len(known_label))
                if max_len == 0:
                    continue

                # A. Raw Levenshtein
                sim_raw = 1 - (Levenshtein.distance(submitted_label, known_label) / max_len)

                # B. Leet-speak normalized
                sim_leet = 1 - (Levenshtein.distance(label_leet, known_label) / max(len(label_leet), len(known_label)))

                # C. Homoglyph normalized
                sim_homo = 1 - (Levenshtein.distance(label_homoglyph, known_label) / max(len(label_homoglyph), len(known_label)))

                # D. Full normalization (leet + homoglyph combined)
                sim_full = 1 - (Levenshtein.distance(label_full, known_label) / max(len(label_full), len(known_label)))

                # E. Substring check — known brand appears verbatim inside submitted label
                #    e.g. "paypal-secure-login" contains "paypal" → definitive signal
                sim_substring = 0.88 if (
                    known_label and (
                        # Standard 4+ char substring match
                        (len(known_label) >= 4 and (known_label in label_full or known_label in label_stripped)) or
                        # 3-char exact component match (catches acronyms like GTB, UBA in compound domains)
                        (len(known_label) >= 3 and known_label in label_components)
                    )
                ) else 0.0

                # F. Hyphen-component check — each part of a compound domain checked individually
                #    e.g. "netfl1x-billing" → "netfllx" vs "netflix" = 86% → caught!
                #    A slight penalty (×0.94) since adding a suffix is deceptive but less severe
                #    than an exact domain match.
                sim_component = 0.0
                for component in label_components:
                    if len(component) < 3:
                        continue
                    comp_max = max(len(component), len(known_label))
                    if comp_max == 0:
                        continue
                    c_sim = 1 - (Levenshtein.distance(component, known_label) / comp_max)
                    sim_component = max(sim_component, c_sim * 0.94)  # 6% penalty for suffix addition

                final_sim = max(sim_raw, sim_leet, sim_homo, sim_full, sim_substring, sim_component)


                if final_sim > highest_similarity:
                    highest_similarity = final_sim
                    closest_brand_label = known_label

            # Generic fallback heuristics for brands not in the list
            if highest_similarity < 0.75:
                # Define a small set of high‑risk generic keywords often used in phishing domains
                _GENERIC_KEYWORDS = {"customs", "login", "secure", "verify", "bank", "delivery", "shipment", "parcel", "payment", "refund"}
                # Tokenize the submitted label on hyphens and dots
                tokens = set(submitted_label.replace(".", "-").split("-"))
                intersect = _GENERIC_KEYWORDS.intersection(tokens)
                if intersect:
                    # Use the first matched generic keyword as a pseudo‑brand for advisory purposes
                    closest_brand_label = list(intersect)[0]
                    highest_similarity = 0.5  # Assign a moderate similarity to trigger advice
                # If no generic keyword matches, keep highest_similarity as‑is (likely 0) and closest_brand_label as None

            # Threshold 0.75 — tighter than before since our dataset is 10x larger
            is_impersonation = (highest_similarity >= 0.75)

            red_flag = None
            closest_domain = f"{closest_brand_label}.com" if closest_brand_label else None
            if is_impersonation:
                red_flag = (
                    f"Typosquatting detected: '{submitted_domain}' is impersonating "
                    f"'{closest_brand_label}' (a globally recognized brand)."
                )

            finding = f"Cross-referenced against global brand intelligence database. No fraudulent matches detected."
            if is_impersonation:
                finding = f"CRITICAL: Visual signature match detected for '{closest_brand_label}'. Integrity Score: {highest_similarity*100:.1f}%."
            elif highest_similarity > 0.5:
                finding = f"Anomalous similarity ({highest_similarity*100:.1f}%) to verified brand '{closest_brand_label}' detected."

            return BrandAgentResult(
                is_impersonation=is_impersonation,
                similarity_score=round(highest_similarity, 4),
                closest_brand=closest_brand_label,
                legitimate_domain=closest_domain,
                red_flag=red_flag,
                finding=finding
            )

        except Exception as e:
            print(f"[BrandAgent] Error: {e}")
            return BrandAgentResult(is_impersonation=False, similarity_score=0.0)
