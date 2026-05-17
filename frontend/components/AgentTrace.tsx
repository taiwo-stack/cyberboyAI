"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Bot, Database, Brain, Zap, Shield, Eye } from "lucide-react";
import { AgentTrace as AgentTraceType } from "@/lib/api";

export default function AgentTrace({ trace }: { trace: AgentTraceType[] }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!trace || trace.length === 0) return null;

  // Dynamic threat color based on score
  const getThreatColor = (score: number) => {
    if (score >= 0.75) return { bar: "bg-red-500", text: "text-red-400", border: "border-red-500/40", glow: "shadow-red-500/10" };
    if (score >= 0.35) return { bar: "bg-yellow-500", text: "text-yellow-400", border: "border-yellow-500/40", glow: "shadow-yellow-500/10" };
    return { bar: "bg-emerald-500", text: "text-emerald-400", border: "border-emerald-500/40", glow: "shadow-emerald-500/10" };
  };

  // Static agent identity styling (icon + badge color — always the same per agent)
  const getAgentIdentity = (agentName: string) => {
    switch (agentName.toLowerCase()) {
      case "brand":
        return { color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", icon: <Shield className="w-4 h-4" />, label: "BRAND" };
      case "lookup":
        return { color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", icon: <Database className="w-4 h-4" />, label: "LOOKUP" };
      case "ml":
        return { color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20", icon: <Brain className="w-4 h-4" />, label: "ML" };
      case "openai":
      case "claude":
        return { color: "text-cyan-400", bg: "bg-cyan-500/10", border: "border-cyan-500/20", icon: <Bot className="w-4 h-4" />, label: "OPENAI" };
      case "cloaking":
        return { color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/20", icon: <Eye className="w-4 h-4" />, label: "CLOAKING" };
      case "network":
      case "whitelist":
        return { color: "text-slate-400", bg: "bg-slate-800", border: "border-slate-700", icon: <Zap className="w-4 h-4" />, label: agentName.toUpperCase() };
      default:
        return { color: "text-slate-400", bg: "bg-slate-800", border: "border-slate-700", icon: <Zap className="w-4 h-4" />, label: agentName.toUpperCase() };
    }
  };

  // Threat level label
  const getThreatLabel = (score: number) => {
    if (score >= 0.75) return { label: "HIGH RISK", color: "text-red-400" };
    if (score >= 0.35) return { label: "CAUTION", color: "text-yellow-400" };
    return { label: "CLEAN", color: "text-emerald-400" };
  };

  return (
    <div className="w-full max-w-3xl mx-auto mt-6 animate-in fade-in duration-700">
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full p-4 flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none"
        >
          <span className="font-semibold text-sm uppercase tracking-wider flex items-center gap-2">
            Agent Pipeline
            <span className="text-slate-500 font-normal normal-case tracking-normal text-xs">
              ({trace.length} agents ran)
            </span>
          </span>
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>

        {isOpen && (
          <div className="p-4 border-t border-slate-800 space-y-3">
            {trace.map((item, idx) => {
              const identity = getAgentIdentity(item.agent);
              const threat = getThreatColor(item.score);
              const level = getThreatLabel(item.score);
              const pct = Math.round(item.score * 100);

              return (
                <div
                  key={idx}
                  className={`bg-slate-950 rounded-lg p-4 border ${threat.border} shadow-sm ${threat.glow}`}
                >
                  {/* Agent header */}
                  <div className="flex justify-between items-center mb-3">
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${identity.bg} ${identity.color} ${identity.border} border`}>
                      {identity.icon}
                      {identity.label}
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Threat level badge */}
                      <span className={`text-xs font-bold uppercase tracking-wider ${level.color}`}>
                        {level.label}
                      </span>
                      <div className="text-slate-500 text-xs font-mono">{item.duration_ms}ms</div>
                    </div>
                  </div>

                  {/* Score bar — color changes dynamically with threat level */}
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${threat.bar} transition-all duration-1000 rounded-full`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className={`text-sm font-mono font-bold w-10 text-right ${threat.text}`}>
                      {pct}%
                    </div>
                  </div>

                  {/* Finding */}
                  <p className="text-slate-300 text-sm leading-relaxed">
                    &gt; {item.finding}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
