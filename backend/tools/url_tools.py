import math
import tldextract
import re
from urllib.parse import urlparse
from tools.whois_tools import get_domain_age_days

# Common URL shorteners
SHORTENERS = {"bit.ly", "goo.gl", "tinyurl.com", "t.co", "rebrand.ly", "is.gd", "buff.ly", "ow.ly"}

def calculate_entropy(string: str) -> float:
    """Calculates the Shannon entropy of a string."""
    if not string:
        return 0.0
    prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(list(string))]
    entropy = -sum([p * math.log(p) / math.log(2.0) for p in prob])
    return entropy

def get_vowel_consonant_ratio(string: str) -> float:
    vowels = "aeiou"
    v_count = sum(1 for c in string.lower() if c in vowels)
    c_count = sum(1 for c in string.lower() if c.isalpha() and c not in vowels)
    if c_count == 0: return 0.0
    return v_count / c_count

def get_max_consecutive_chars(string: str) -> int:
    if not string: return 0
    max_count = 0
    current_count = 1
    for i in range(1, len(string)):
        if string[i] == string[i-1]:
            current_count += 1
        else:
            max_count = max(max_count, current_count)
            current_count = 1
    return max(max_count, current_count)

def extract_features(url: str, skip_whois: bool = False) -> dict:
    """
    Extracts 17+ behavioral features from a URL for robust ML analysis.
    V3 Update: Normalizes URL and strips 'www.' to avoid subdomain bias.
    """
    try:
        # NORMALIZE
        url = url.strip().rstrip('/')
        parsed = urlparse(url)
        ext = tldextract.extract(url)
        
        # Strip 'www.' for domain-specific lexical checks
        domain_part = ext.domain
        domain_full = f"{ext.domain}.{ext.suffix}"
        
        # --- BASE FEATURES ---
        if skip_whois:
            domain_age = 180
        else:
            raw_domain_age = get_domain_age_days(domain_full)
            # -1 means WHOIS is blocked/private/timed-out — use neutral 180 days
            # so the ML model doesn't treat "unknown" as "brand-new domain (high risk)"
            domain_age = raw_domain_age if raw_domain_age >= 0 else 180

        brand_similarity = 0.0 # Placeholder
        
        keywords = ["verify", "secure", "otp", "login", "update", "bvn", "bank", "alert", "signin", "account"]
        keyword_count = sum(1 for kw in keywords if kw in url.lower())
        
        entropy = calculate_entropy(domain_part)
        
        # Subdomain depth WITHOUT counting www
        sub_clean = ext.subdomain.replace('www', '').strip('.')
        subdomain_depth = len(sub_clean.split('.')) if sub_clean else 0
        
        is_https = 1 if parsed.scheme == "https" else 0
        url_length = len(url)
        hyphen_count = domain_part.count('-')
        
        risky_tlds = [".xyz", ".tk", ".top", ".ml", ".ga", ".cf", ".gq"]
        tld_risk_score = 0.8 if any(ext.suffix.endswith(t[1:]) for t in risky_tlds) else 0.1
        
        special_char_count = sum(url.count(c) for c in ['@', '=', '?', '_', '&'])
        
        lookalike_numbers = ['0', '1', '3', '5']
        num_sub_count = sum(domain_part.count(n) for n in lookalike_numbers)
        numeric_substitution = num_sub_count / len(domain_part) if domain_part else 0.0
        
        # --- ROBUSTNESS FEATURES ---
        percent_encoding_count = url.count('%')
        path_part = url[url.find("//")+2:]
        double_slash_redirect = 1 if "//" in path_part else 0
        
        # New features
        path_only = parsed.path
        path_depth = len([p for p in path_only.split('/') if p]) if path_only else 0
        
        suspicious_exts = ['.php', '.exe', '.apk', '.zip', '.jar', '.scr', '.bin']
        has_suspicious_extension = 1 if any(path_only.lower().endswith(ext) for ext in suspicious_exts) else 0
        
        suspicious_sub_keywords = ["login", "verify", "secure", "auth", "account", "update", "webmail", "support", "service", "billing"]
        suspicious_subdomain = 1 if any(kw in sub_clean.lower() for kw in suspicious_sub_keywords) else 0
        
        is_ip_address = 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain_part) else 0
        v_c_ratio = get_vowel_consonant_ratio(domain_part)
        consecutive_chars = get_max_consecutive_chars(domain_part)
        is_shortened = 1 if domain_full in SHORTENERS else 0
        
        has_non_standard_port = 0
        if parsed.port and parsed.port not in [80, 443]:
            has_non_standard_port = 1
            
        redirect_count = 0 # Placeholder
        
        return {
            "domain_age_days": domain_age,
            "brand_similarity": brand_similarity,
            "keyword_count": keyword_count,
            "entropy": entropy,
            "subdomain_depth": subdomain_depth,
            "is_https": is_https,
            "url_length": url_length,
            "hyphen_count": hyphen_count,
            "tld_risk_score": tld_risk_score,
            "special_char_count": special_char_count,
            "numeric_substitution": numeric_substitution,
            "percent_encoding_count": percent_encoding_count,
            "double_slash_redirect": double_slash_redirect,
            "is_ip_address": is_ip_address,
            "v_c_ratio": v_c_ratio,
            "consecutive_chars": consecutive_chars,
            "is_shortened": is_shortened,
            "has_non_standard_port": has_non_standard_port,
            "redirect_count": redirect_count,
            "path_depth": path_depth,
            "has_suspicious_extension": has_suspicious_extension,
            "suspicious_subdomain": suspicious_subdomain
        }
    except Exception:
        return {}
