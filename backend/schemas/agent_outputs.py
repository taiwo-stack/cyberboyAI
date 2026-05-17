from pydantic import BaseModel
from typing import Optional, List

class BrandAgentResult(BaseModel):
    is_impersonation: bool
    similarity_score: float
    closest_brand: Optional[str] = None
    legitimate_domain: Optional[str] = None
    red_flag: Optional[str] = None
    finding: str = ""
    execution_ms: int = 0

class LookupAgentResult(BaseModel):
    db_score: float
    matched: bool
    sources_flagged: List[str]
    phishtank_hit: bool
    abuseipdb_score: int
    otx_hit: bool
    community_hit: bool
    finding: str = ""
    execution_ms: int = 0

class MLAgentResult(BaseModel):
    ml_score: float
    features: dict
    high_risk_features: List[str]
    threat_type: str = "benign"
    finding: str = ""
    execution_ms: int = 0

class OpenAIAgentResult(BaseModel):
    openai_score: float
    confidence: int
    red_flags: List[str]
    explanation: str
    advice: str
    threat_type: str
    identified_brand: Optional[str] = None
    official_domain: Optional[str] = None
    finding: str = ""
    execution_ms: int = 0

class AgentTrace(BaseModel):
    agent: str
    score: float
    finding: str
    duration_ms: int

class BehavioralAgentResult(BaseModel):
    behavior_score: float
    red_flags: List[str]
    redirect_chain: List[str]
    ssl_issuer: str
    dynamic_findings: dict
    finding: str = ""
    raw_html: str = ""
    raw_text: str = ""
    execution_ms: int = 0

class EmailAgentResult(BaseModel):
    email_score: float
    threat_type: str = "benign"
    finding: str = ""
    execution_ms: int = 0

class VerdictResponse(BaseModel):
    verdict: str
    score: float
    red_flags: List[str]
    explanation: str
    advice: str
    threat_type: str = "benign"
    identified_brand: Optional[str] = None
    agents_used: List[str]
    agent_trace: List[AgentTrace]
    brand_result: Optional[BrandAgentResult] = None
    lookup_result: Optional[LookupAgentResult] = None
    ml_result: Optional[MLAgentResult] = None
    openai_result: Optional[OpenAIAgentResult] = None
    behavior_result: Optional[BehavioralAgentResult] = None
    email_result: Optional[EmailAgentResult] = None
    processing_ms: int
