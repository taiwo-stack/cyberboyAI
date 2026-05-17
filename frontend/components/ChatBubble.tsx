"use client";

import { 
  AlertTriangle, Bot, Flame, CheckCircle, ShieldAlert, 
  Database, Globe, Ban, RefreshCw, Activity, Lock, Brain, Shield
} from "lucide-react";
import { VerdictResponse } from "@/lib/api";
import { useTypewriter } from "@/hooks/useTypewriter";
import DeepEvidence from "./DeepEvidence";
import AnimatedAgentTrace from "./AnimatedAgentTrace";
import RiskGauge from "./RiskGauge";

type MessageProps = {
  role: "user" | "ai";
  content?: string;
  verdictData?: VerdictResponse;
  onRetry?: (input: string) => void;
};

// Sub-component that types out a single string
function Typed({ text, speed = 12 }: { text: string; speed?: number }) {
  const { displayed, done } = useTypewriter(text, speed);
  return <span className={!done ? "typing-cursor" : ""}>{displayed}</span>;
}

export default function ChatBubble({ role, content, verdictData, onRetry }: MessageProps) {

  // ── User bubble ────────────────────────────────────────────────────────────
  if (role === "user") {
    return (
      <div className="flex justify-end mb-6 w-full fade-in group">
        <div className="flex flex-col items-end gap-1.5">
          <div className="bg-blue-600/20 border border-blue-500/30 text-blue-50 max-w-[85%] sm:max-w-xl rounded-2xl rounded-tr-none px-6 py-4 shadow-lg">
            <p className="text-lg leading-relaxed break-all font-mono">&gt; {content}</p>
          </div>
          {onRetry && content && (
            <button
              onClick={() => onRetry(content)}
              title="Re-run this scan"
              className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-blue-400 font-mono transition-colors opacity-0 group-hover:opacity-100"
            >
              <RefreshCw className="w-3 h-3" />
              retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // ── Plain AI text bubble (greeting / error) ────────────────────────────────
  if (!verdictData && content) {
    return (
      <div className="flex justify-start mb-8 w-full fade-in">
        <div className="flex gap-4 max-w-3xl w-full">
          <div className="w-10 h-10 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(37,99,235,0.3)]">
            <Bot className="w-6 h-6 text-blue-400" />
          </div>
          <div className="pt-2 text-slate-300 leading-relaxed font-mono text-sm">
            <Typed text={content} speed={10} />
          </div>
        </div>
      </div>
    );
  }

  // ── Full Verdict Bubble ────────────────────────────────────────────────────
  if (verdictData) {
    const isSafe = verdictData.verdict === "SAFE";
    const isSusp = verdictData.verdict === "SUSPICIOUS";
    const isInvalid = verdictData.verdict === "INVALID DOMAIN";

    const theme = isInvalid ? {
      head: "bg-slate-500/10 text-slate-400 border-slate-600/40",
      icon: <Ban className="w-6 h-6 text-slate-500" />,
      label: "text-slate-400",
    } : isSafe ? {
      head: "bg-green-500/10 text-green-400 border-green-600/40",
      icon: <CheckCircle className="w-6 h-6 text-green-500" />,
      label: "text-green-400",
    } : isSusp ? {
      head: "bg-amber-500/10 text-amber-400 border-amber-600/40",
      icon: <AlertTriangle className="w-6 h-6 text-amber-400" />,
      label: "text-amber-400",
    } : {
      head: "bg-red-500/10 text-red-400 border-red-600/40",
      icon: <ShieldAlert className="w-6 h-6 text-red-500" />,
      label: "text-red-400",
    };

    return (
      <div className="flex justify-start mb-8 w-full fade-in">
        <div className="flex gap-4 max-w-4xl w-full">

          {/* Bot Avatar */}
          <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(59,130,246,0.15)]">
            <Bot className="w-6 h-6 text-blue-400" />
          </div>

          <div className="flex-1 space-y-4">

            {/* ── Terminal header bar ── */}
            <div className={`rounded-xl border p-5 ${theme.head} shadow-xl`}>
              <div className="flex items-center gap-3 mb-3">
                {/* Stoplight dots */}
                <div className="flex gap-1.5 mr-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                    <span className="w-2.5 h-2.5 rounded-full bg-yellow-400/60" />
                    <span className="w-2.5 h-2.5 rounded-full bg-green-400/60" />
                </div>
                <span className="font-mono text-[11px] opacity-40 tracking-widest">CYBERBOY_AI · THREAT_ENGINE_v3</span>
                <span className="ml-auto font-mono text-[11px] border border-current px-2 py-0.5 rounded opacity-60">
                  CONFIDENCE {verdictData.verdict === "SAFE"
                    ? Math.round((1 - verdictData.score) * 100)
                    : Math.round(verdictData.score * 100)}%
                </span>
              </div>

              <div className="flex items-center gap-4 mb-3 border-t border-white/5 pt-4">
                <RiskGauge score={verdictData.score} verdict={verdictData.verdict} />
                <div className="flex items-center gap-3">
                    <h3 className={`text-xl font-black uppercase tracking-widest font-mono ${theme.label}`}>
                        {verdictData.verdict}
                    </h3>
                    {verdictData.threat_type && verdictData.threat_type !== 'benign' && (
                        <span className="px-2 py-0.5 rounded bg-white/10 border border-white/10 text-[9px] font-black uppercase tracking-tighter">
                            {verdictData.threat_type}
                        </span>
                    )}
                </div>
              </div>

              <p className="font-mono text-sm opacity-80 leading-relaxed">
                <Typed text={verdictData.explanation} speed={8} />
              </p>
            </div>

            {/* ── Animated Agent Trace (Terminal View) ── */}
            {verdictData.agent_trace && verdictData.agent_trace.length > 0 && (
              <AnimatedAgentTrace trace={verdictData.agent_trace} />
            )}

            {/* ── Red Flags ── */}
            {verdictData.red_flags.length > 0 && (
              <div className="bg-[#0d0607] rounded-xl p-4 border border-red-900/30 font-mono shadow-lg">
                <h4 className="text-[11px] font-semibold mb-2 flex items-center gap-2 text-orange-400 uppercase tracking-widest">
                  <Flame className="w-3.5 h-3.5" /> CRITICAL_THREAT_INDICATORS
                </h4>
                <ul className="space-y-1.5">
                  {verdictData.red_flags.map((flag, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-[11px] text-slate-300">
                      <span className="text-orange-500 mt-0.5 animate-pulse">!</span>
                      <span className="leading-snug">{flag}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* ── Deep Technical Evidence (New Section) ── */}
            <DeepEvidence verdict={verdictData} />

            {/* ── Advice ── */}
            <div className="bg-[#050f1d] border-l-4 border-l-blue-600 px-5 py-4 rounded-r-xl font-mono text-[12px] shadow-lg">
              <span className="text-blue-500 font-bold mr-2 uppercase tracking-widest">[ADVISORY]</span>
              <span className="text-blue-200/90 leading-relaxed">{verdictData.advice}</span>
            </div>

          </div>
        </div>
      </div>
    );
  }

  return null;
}
