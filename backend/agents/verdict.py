import time
from typing import Optional
from schemas.agent_outputs import (
    BrandAgentResult, LookupAgentResult, MLAgentResult,
    OpenAIAgentResult, BehavioralAgentResult, EmailAgentResult, AgentTrace, VerdictResponse
)

async def compute_verdict(
    brand: BrandAgentResult,
    lookup: LookupAgentResult,
    ml: MLAgentResult,
    openai: Optional[OpenAIAgentResult],
    behavior: Optional[BehavioralAgentResult],
    email: Optional[EmailAgentResult],
    start_time: float,
    sms_urgent: bool = False,
    sms_msg: str = "",
    is_trusted_domain: bool = False
) -> VerdictResponse:
    """
    Combines agent scores into one final verdict using fast paths and weighted standard paths.
    """
    # 1. FAST PATH 1 — Definitive database match
    if lookup.matched and lookup.db_score >= 0.95:
        verdict = "DANGEROUS"
        score = 1.0
        explanation = "This URL is in a known threat database."
    # 2. FAST PATH 2 — Near-perfect brand impersonation
    elif brand.is_impersonation and brand.similarity_score >= 0.90:
        verdict = "DANGEROUS"
        score = 0.97
        explanation = f"This domain is impersonating {brand.closest_brand}."
    # 3. STANDARD PATH — Weighted scoring
    else:
        # Use ML score if OpenAI is not available
        openai_score = openai.openai_score if openai else ml.ml_score
        behavior_score = behavior.behavior_score if behavior else 0.0

        # OFFLINE DETECTION: If OpenAI or ML flagged the domain as unreachable/NXDOMAIN
        is_offline = openai and any(
            kw in f.lower() for f in openai.red_flags
            for kw in ("unreachable", "nxdomain", "service unavailable", "dns failure")
        )

        # ── Consensus-Aware Scoring ───────────────────────────────────────────
        # ML and OpenAI work together. Neither overrides the other by default.
        # Weights shift based on whether they agree and how strong the evidence is.
        score_gap = abs(ml.ml_score - openai_score)
        openai_has_evidence = openai and len(openai.red_flags) > 0
        openai_confident = openai and openai.confidence >= 65

        if is_offline:
            # Offline: no live page to observe — ML structure + OpenAI URL reasoning
            lookup_w, ml_w, openai_w, behavior_w = 0.10, 0.45, 0.35, 0.10

        elif score_gap <= 0.30:
            # ── Agreement Zone ──────────────────────────────────────────────────
            # Standard weights: Lookup (35%), ML (30%), AI (20%), Behavior (15%)
            lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.30, 0.20, 0.15

        elif ml.ml_score > openai_score:
            # ── ML says risky, OpenAI says safe ─────────────────────────────────
            # OpenAI actually visited the page. Its clean verdict deserves more weight
            # IF it is confident AND found no specific red flags (i.e. it saw legitimacy).
            if openai_confident and not openai_has_evidence:
                lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.20, 0.30, 0.15
            elif openai_confident and openai_has_evidence:
                lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.25, 0.25, 0.15
            else:
                lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.35, 0.15, 0.15

        else:
            # ── OpenAI says risky, ML says safe ─────────────────────────────────
            # This is the most dangerous disagreement case:
            # ML only sees structure; OpenAI saw actual credential forms or social engineering.
            if openai_confident and openai_has_evidence:
                lookup_w, ml_w, openai_w, behavior_w = 0.30, 0.15, 0.40, 0.15
            elif openai_confident:
                lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.20, 0.30, 0.15
            else:
                # OpenAI low confidence — standard weights
                lookup_w, ml_w, openai_w, behavior_w = 0.35, 0.30, 0.20, 0.15

        final = (lookup.db_score * lookup_w) + (ml.ml_score * ml_w) + (openai_score * openai_w) + (behavior_score * behavior_w)

        # Apply brand, combination, and SMS boosts AFTER consensus weights
        if brand.is_impersonation:
            final = min(final + 0.30, 1.0)
        elif brand.similarity_score >= 0.60:
            boost = (brand.similarity_score - 0.60) * 1.0
            final = min(final + boost, 1.0)

        has_risky_tld = any(f == "High-risk TLD detected" for f in ml.high_risk_features)
        has_keyword = ml.features.get("keyword_count", 0) > 0 if ml.features else False
        if brand.similarity_score >= 0.55 and (has_risky_tld or has_keyword):
            final = min(final + 0.20, 1.0)

        if sms_urgent:
            final = min(final + 0.15, 1.0)
            
        if email and email.email_score >= 0.5:
            final = min(final + 0.20, 1.0)

        # TRUSTED DOMAIN OVERRIDE: If the domain is globally trusted (e.g., Amazon, Google)
        # and it didn't hit the threat-intel database fast-path, it is almost certainly safe.
        # We squash the ML/OpenAI score to prevent false positives from datasets or forms,
        # unless OpenAI explicitly found a high-confidence credential harvesting form (>=0.95).
        if is_trusted_domain:
            is_abuse_detected = (openai and openai.openai_score >= 0.95 and "credential" in " ".join(openai.red_flags).lower())
            if not is_abuse_detected:
                final = 0.02 # Extremely safe
                # Clear OpenAI result noise (like generic phishing explanations)
                if openai:
                    openai = openai.model_copy(update={"red_flags": [], "openai_score": 0.02})
                # Clear ML noise
                ml.high_risk_features = []
                # Clear Behavioral noise (False Positive cloaking/SSL on big sites)
                if behavior:
                    behavior = behavior.model_copy(update={
                        "red_flags": [], 
                        "behavior_score": 0.0,
                        "finding": behavior.finding.replace(" | CLOAKING DETECTED", "")
                    })

        score = round(final, 4)
        
        # VERDICT THRESHOLDS
        if score >= 0.75:
            verdict = "DANGEROUS"
            explanation = openai.explanation if (openai and openai.openai_score >= 0.75) else "This URL shows clear signs of phishing based on ML and AI analysis."
            if sms_urgent:
                explanation = "This URL shows clear signs of phishing and uses urgent social engineering tactics in the message."
        elif score >= 0.35:
            verdict = "SUSPICIOUS"
            explanation = openai.explanation if (openai and openai.openai_score >= 0.35) else "This URL has several anomalous mathematical characteristics that warrant caution."
        else:
            verdict = "SAFE"
            if ml.high_risk_features:
                flags = [f.lower().replace(" detected", "").strip() for f in ml.high_risk_features]
                feats_str = ", ".join(flags)
                explanation = f"While this link possesses technical risk factors like a {feats_str}, it does not match against any global phishing databases and isn't impersonating known brands. The system therefore concludes it is a legitimate site with a slightly irregular domain structure."
            else:
                explanation = "This URL has a clean structure and shows no immediate signs of phishing across any threat intelligence channels."
                
            if sms_urgent:
                explanation = "The URL itself appears structurally safe, but the message phrasing uses urgent tactics common in scams. Proceed with caution."
            elif email and email.email_score >= 0.5:
                explanation = "The URL itself appears safe, but the email content is highly suspicious. Proceed with caution."

    # ASSEMBLE red_flags list
    red_flags = []
    if brand.red_flag:
        red_flags.append(brand.red_flag)
    if sms_msg:
        red_flags.append(sms_msg)
    if email and email.email_score >= 0.5:
        red_flags.append(f"Suspicious email content detected ({email.email_score*100:.1f}% risk)")
    if ml.high_risk_features:
        red_flags.extend(ml.high_risk_features)
    if openai and openai.red_flags:
        red_flags.extend(openai.red_flags)
    if behavior and behavior.red_flags:
        red_flags.extend(behavior.red_flags)
    if lookup.phishtank_hit:
        red_flags.append("Found in OpenPhish/URLhaus threat database")
    if lookup.abuseipdb_score > 50:
        red_flags.append("Reported as malicious IP (AbuseIPDB)")
    if lookup.otx_hit:
        red_flags.append("Flagged by AlienVault OTX threat intelligence")
    if lookup.community_hit:
        red_flags.append("Matches community-reported global threat")

    # ASSEMBLE advice
    advice_parts = []
    red_flag_str = " ".join(red_flags).lower()
    
    if verdict == "DANGEROUS":
        if openai and openai.openai_score >= 0.75 and openai.advice:
            advice = openai.advice
        else:
            advice_parts.append("CRITICAL ACTION REQUIRED: Do not interact with this page.")
            if brand.is_impersonation:
                advice_parts.append(f"It is actively attempting to impersonate {brand.closest_brand}.")
            # Dynamic recovery advice via lightweight OpenAI call
            import os
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            
            if brand.is_impersonation and api_key:
                try:
                    client = AsyncOpenAI(api_key=api_key)
                    resp = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=0.2,
                        max_tokens=100,
                        messages=[{
                            "role": "system",
                            "content": f"Generate a strict, 2-sentence security warning for a user who clicked a phishing link impersonating {brand.closest_brand}. Advise them on immediate next steps based on the brand's industry. Do not use generic placeholders."
                        }]
                    )
                    advice_parts.append(resp.choices[0].message.content.strip())
                except Exception as e:
                    print(f"Advice generation error: {e}")
                    advice_parts.append("Change your password on the real website and enable two-factor authentication.")
            else:
                advice_parts.append("Change your password on the real website and enable two-factor authentication.")

            if "ip address" in red_flag_str:
                advice_parts.append("Legitimate services will never use bare IP addresses for logins.")
            if sms_urgent:
                advice_parts.append("The message urgency is a classic psychological tactic designed to induce panic.")
            advice = " ".join(advice_parts)

        
    elif verdict == "SUSPICIOUS":
        if openai and openai.openai_score >= 0.35 and openai.advice:
            advice = openai.advice
        else:
            advice_parts.append("PROCEED WITH EXTREME CAUTION.")
            if brand.closest_brand and brand.similarity_score >= 0.5:
                advice_parts.append(f"The domain name appears suspiciously similar to {brand.closest_brand}.")
            if "numeric" in red_flag_str or "high-risk tld" in red_flag_str or "unusual url path" in red_flag_str or "entropy" in red_flag_str:
                advice_parts.append("The mathematical structure of the link is highly irregular for a legitimate corporate entity.")
            if sms_urgent:
                advice_parts.append("Keep your guard up; the text message is using demanding social engineering phrasing.")
            advice_parts.append("Do not trust this link directly. Open a new browser tab and manually search for the intended primary website.")
            advice = " ".join(advice_parts)
        
    else:
        if red_flags:
            advice = "This URL triggered some minor structural warnings, but our deep scans found no active malice. It is safe to browse, but avoid downloading unexpected files."
        else:
            advice = "This link checked out perfectly clean across all 8 security layers. You are completely safe to proceed."

    # ASSEMBLE agent_trace list with rich descriptions
    brand_finding = brand.red_flag if brand.red_flag else "No brand impersonation detected."
    
    if lookup.matched:
        feeds = ", ".join(lookup.sources_flagged) if lookup.sources_flagged else "global threat feeds"
        lookup_finding = f"Flagged as malicious by {feeds}."
    else:
        lookup_finding = "Scanned clean across 5 global threat intelligence feeds."

    feat_count = len(ml.features) if ml.features else 0
    anomaly_count = len(ml.high_risk_features) if ml.high_risk_features else 0
    ml_score_pct = round(ml.ml_score * 100, 1)

    trace = []
    trace.append(AgentTrace(agent="brand", score=brand.similarity_score, finding=brand.finding or "No brand impersonation detected.", duration_ms=brand.execution_ms))
    trace.append(AgentTrace(agent="lookup", score=lookup.db_score, finding=lookup.finding or "Scanned clean across feeds.", duration_ms=lookup.execution_ms))
    trace.append(AgentTrace(agent="ml", score=ml.ml_score, finding=ml.finding or f"Analyzed {len(ml.features)} features.", duration_ms=ml.execution_ms))
    
    if openai:
        trace.append(AgentTrace(agent="openai", score=openai.openai_score, finding=openai.finding or f"AI Analysis: {openai.explanation}", duration_ms=openai.execution_ms))
    if behavior:
        trace.append(AgentTrace(agent="behavior", score=behavior.behavior_score, finding=behavior.finding or "Behavioral scan complete.", duration_ms=behavior.execution_ms))
    if email:
        trace.append(AgentTrace(agent="email", score=email.email_score, finding=email.finding or "Email analysis complete.", duration_ms=email.execution_ms))

    # Threat Type Logic
    threat_type = "benign"
    red_flag_str = " ".join(red_flags).lower()
    if verdict != "SAFE":
        if openai and openai.threat_type and openai.threat_type != "benign":
            threat_type = openai.threat_type
        elif ml.threat_type != "benign":
            threat_type = ml.threat_type
        elif brand.is_impersonation or (openai and openai.identified_brand and openai.openai_score > 0.6):
            threat_type = "phishing"
        elif lookup.abuseipdb_score > 50 or lookup.otx_hit:
            threat_type = "malware"
        elif "credential" in red_flag_str or "login" in red_flag_str:
            threat_type = "phishing"
        else:
            threat_type = "phishing" # default fallback for dangerous URLs

    return VerdictResponse(
        verdict=verdict,
        score=score,
        red_flags=red_flags,
        explanation=explanation,
        advice=advice,
        threat_type=threat_type,
        agents_used=["brand", "lookup", "ml"] + (["openai"] if openai else []),
        agent_trace=trace,
        brand_result=brand,
        lookup_result=lookup,
        ml_result=ml,
        openai_result=openai,
        behavior_result=behavior,
        email_result=email,
        processing_ms=int((time.time() - start_time) * 1000)
    )
