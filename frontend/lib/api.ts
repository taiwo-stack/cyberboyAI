export type AgentTrace = {
  agent: string;
  score: number;
  finding: string;
  duration_ms: number;
};

export type VerdictResponse = {
  verdict: "SAFE" | "SUSPICIOUS" | "DANGEROUS" | "INVALID DOMAIN" | "GREETING";
  score: number;
  red_flags: string[];
  explanation: string;
  advice: string;
  threat_type: string;
  identified_brand?: string;
  agents_used: string[];
  agent_trace: AgentTrace[];
  brand_result: any;
  lookup_result: any;
  ml_result: any;
  openai_result: any;
  behavior_result?: any;
  processing_ms: number;
};

export type StatsResponse = {
  total_scans: number;
  dangerous_count: number;
  suspicious_count: number;
  safe_count: number;
  community_threats_count: number;
};

// Use localhost:8000 by default if environment variable is missing
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function analyzeInput(input: string, imageBase64?: string): Promise<VerdictResponse> {
  const payload: any = { input, source: "web" };
  if (imageBase64) {
    payload.image_base64 = imageBase64;
  }

  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Analyze API failed with status ${response.status}`);
  }

  return response.json();
}

export async function getStats(): Promise<StatsResponse> {
  const response = await fetch(`${API_URL}/stats`);
  
  if (!response.ok) {
    throw new Error(`Stats API failed with status ${response.status}`);
  }
  
  return response.json();
}
