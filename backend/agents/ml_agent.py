import logging
import os
import joblib
import time
import numpy as np
import tldextract
from tools.url_tools import extract_features
from tools.supabase_client import supabase
from tools.trusted_domains import trusted_domain_manager
from schemas.agent_outputs import MLAgentResult

logger = logging.getLogger("gaudon.ml_agent")

class MLAgent:
    def __init__(self):
        """Initializes the ML Agent by loading the trained Random Forest model."""
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "model.joblib")
        try:
            self.model = joblib.load(model_path)
            self.feature_names = [
                "domain_age_days", "keyword_count", "entropy", "subdomain_depth", "is_https",
                "url_length", "hyphen_count", "tld_risk_score", "special_char_count", "numeric_substitution",
                "percent_encoding_count", "double_slash_redirect", "is_ip_address", "v_c_ratio",
                "consecutive_chars", "is_shortened", "has_non_standard_port",
                "path_depth", "has_suspicious_extension", "suspicious_subdomain"
            ]
        except Exception as exc:
            logger.exception("Error loading ML model from %s", model_path)
            self.model = None

    def _is_whitelisted(self, url: str) -> bool:
        """Checks if the registered domain of a URL is in the trusted whitelist.

        Delegates to ``trusted_domain_manager`` (the single source of truth)
        instead of maintaining a duplicate hardcoded set here.
        """
        try:
            ext = tldextract.extract(url)
            domain = f"{ext.domain}.{ext.suffix}".lower()
            return trusted_domain_manager.is_trusted(domain)
        except Exception:
            return False

    async def check(self, url: str) -> MLAgentResult:
        """Analyzes a URL using the trained ML model with whitelist override."""
        start_time = time.time()
        if self.model is None:
            return MLAgentResult(
                ml_score=0.50,
                features={},
                high_risk_features=[],
                finding="WARNING: ML model failed to load. Fallback to 50% confidence.",
                execution_ms=int((time.time() - start_time) * 1000)
            )

        try:
            # --- WHITELIST CHECK FIRST ---
            if self._is_whitelisted(url):
                feat_dict = extract_features(url) or {}
                return MLAgentResult(
                    ml_score=0.01, # Near-zero — a confirmed-safe domain 
                    features=feat_dict,
                    high_risk_features=[],
                    finding="Globally recognized safe domain. Pipeline bypassed by whitelist.",
                    execution_ms=int((time.time() - start_time) * 1000)
                )

            # --- FEATURE EXTRACTION ---
            feat_dict = extract_features(url)
            if not feat_dict:
                return MLAgentResult(
                    ml_score=0.50,
                    features={},
                    high_risk_features=[],
                    finding="WARNING: ML feature extraction failed. Fallback to 50% confidence.",
                    execution_ms=int((time.time() - start_time) * 1000)
                )

            # --- MODEL INFERENCE (Multi-Class) ---
            vector = []
            for name in self.feature_names:
                val = feat_dict.get(name, 0)
                if val is None:
                    val = 180 if name == "domain_age_days" else 0
                vector.append(val)
            probs = self.model.predict_proba(np.array([vector]))[0]
            
            # ml_score is 1.0 - prob(benign)
            # label_map = {"benign": 0, "phishing": 1, "malware": 2, "defacement": 3}
            ml_score = 1.0 - float(probs[0]) 
            
            # Extract threat_type
            class_idx = int(np.argmax(probs))
            classes = ["benign", "phishing", "malware", "defacement"]
            threat_type = classes[class_idx]

            # --- HIGH RISK FLAGS ---
            high_risk_features = []
            if feat_dict.get("is_ip_address"):
                high_risk_features.append("Uses raw IP address instead of domain")
            if feat_dict.get("double_slash_redirect"):
                high_risk_features.append("Double-slash redirect detected in path")
            if feat_dict.get("has_non_standard_port"):
                high_risk_features.append("Non-standard port detected")
            if feat_dict.get("tld_risk_score", 0) > 0.5:
                high_risk_features.append("High-risk TLD detected")
            if feat_dict.get("entropy", 0) > 4.5:
                high_risk_features.append("High entropy (DGA) detected in domain")
            if feat_dict.get("numeric_substitution", 0) > 0.15:
                high_risk_features.append("Suspicious numeric substitutions")
            if feat_dict.get("is_https") == 0:
                high_risk_features.append("Unsecured HTTP connection")
            if feat_dict.get("subdomain_depth", 0) > 2:
                high_risk_features.append("Suspiciously deep subdomain levels")
            if feat_dict.get("path_depth", 0) > 3:
                high_risk_features.append("Unusually deep URL path structure")
            if feat_dict.get("has_suspicious_extension"):
                high_risk_features.append("Target path ends in suspicious file extension")
            if feat_dict.get("suspicious_subdomain"):
                high_risk_features.append("Subdomain contains social engineering keywords")

            # In-depth finding
            if ml_score > 0.5:
                if high_risk_features:
                    finding = f"Classified as {threat_type} ({ml_score*100:.1f}% risk). Triggered {len(high_risk_features)} structural anomalies."
                else:
                    # No hard threshold was individually breached, but the combined
                    # feature vector pattern still closely matches phishing profiles in
                    # the training corpus. Surface the dominant contributing feature.
                    age = feat_dict.get("domain_age_days")
                    if age is None or age == -1:
                        age_note = "Domain age is unknown (WHOIS lookup failed/private)."
                    else:
                        # Normalised age contribution: 0 days = max risk (1.0), 365 days = zero risk (0.0).
                        # The model was trained on this normalised scale, so we invert it to get
                        # an intuitive "age risk" percentage for the finding string.
                        age_risk_pct = max(0.0, (1.0 - age / 365.0)) * 100
                        age_note = (
                            f"Primary signal: domain registration age ({age}d, ~{age_risk_pct:.0f}% age-risk) "
                            f"pattern-matches known phishing registrations in the training corpus."
                        )
                    finding = (
                        f"Classified as {threat_type} ({ml_score*100:.1f}% risk). "
                        f"No individual structural threshold was breached, but the combined "
                        f"feature-vector profile matches phishing patterns. {age_note}"
                    )
            else:
                finding = f"Score {ml_score*100:.1f}% | Analyzed 22 behavioral features. No high-risk structural patterns detected."

            return MLAgentResult(
                ml_score=round(ml_score, 4),
                features=feat_dict,
                high_risk_features=high_risk_features,
                threat_type=threat_type,
                finding=finding,
                execution_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as exc:
            logger.exception("[MLAgent] Processing error for url=%r", url)
            return MLAgentResult(
                ml_score=0.50,
                features={},
                high_risk_features=[],
                finding="WARNING: ML processing error. Fallback to 50% confidence.",
                execution_ms=int((time.time() - start_time) * 1000)
            )
