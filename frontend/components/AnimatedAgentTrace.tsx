"use client";

import { useState, useEffect } from "react";
import { Database, Shield, Brain, Bot, Activity, Globe, CheckCircle } from "lucide-react";
import { AgentTrace } from "@/lib/api";

const getAgentIcon = (name: string) => {
    switch(name.toLowerCase()) {
        case 'brand': return <Shield className="w-3 h-3" />;
        case 'lookup': return <Database className="w-3 h-3" />;
        case 'ml': return <Brain className="w-3 h-3" />;
        case 'email': return <Brain className="w-3 h-3 text-purple-400" />;
        case 'openai': return <Bot className="w-3 h-3" />;
        case 'behavior': 
        case 'behavioral': return <Activity className="w-3 h-3" />;
        default: return <Globe className="w-3 h-3" />;
    }
};

export default function AnimatedAgentTrace({ trace }: { trace: AgentTrace[] }) {
  const [visibleItems, setVisibleItems] = useState<number>(0);

  useEffect(() => {
    if (visibleItems < trace.length) {
      const timer = setTimeout(() => {
        setVisibleItems(prev => prev + 1);
      }, 700); // 700ms delay per agent appearance
      return () => clearTimeout(timer);
    }
  }, [visibleItems, trace.length]);

  if (!trace || trace.length === 0) return null;

  return (
    <div className="space-y-3 bg-[#050d1a] border border-blue-900/30 rounded-lg p-4 font-mono shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
       <h4 className="text-[10px] font-semibold uppercase tracking-[0.3em] text-blue-500/70 flex items-center gap-2 mb-3 border-b border-blue-900/30 pb-2">
         <Database className="w-3 h-3 animate-pulse" /> SYSTEM_TRACE_LOG
       </h4>
       <div className="space-y-3">
          {trace.map((t, idx) => (
             <div 
               key={idx} 
               className={`transition-all duration-500 ease-out flex flex-col gap-1.5 overflow-hidden ${idx < visibleItems ? 'opacity-100 max-h-24 translate-x-0' : 'opacity-0 max-h-0 -translate-x-4'}`}
             >
                <div className="flex items-center gap-2">
                  <span className="text-green-500 text-[10px] bg-green-500/10 px-1 rounded border border-green-500/20">
                    [{t.duration_ms}ms]
                  </span>
                  <span className="text-blue-400 text-[11px] font-bold uppercase flex items-center gap-1.5">
                     {getAgentIcon(t.agent)} {t.agent}_MODULE
                  </span>
                  <span className="text-slate-600 text-[10px]">::</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border ${t.score >= 0.75 ? 'bg-red-500/10 text-red-400 border-red-500/20' : t.score >= 0.4 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>
                    CONFIDENCE: {(t.score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="pl-[5.5px] text-slate-400 text-[11px] border-l border-slate-700/50 ml-1.5">
                  &gt; {t.finding}
                </div>
             </div>
          ))}
          {visibleItems < trace.length && (
            <div className="text-blue-500/70 text-[11px] flex items-center gap-2 mt-2 font-mono">
               <span className="w-1.5 h-3.5 bg-blue-500 inline-block animate-ping rounded-sm"></span> AWAITING_MODULE_RESPONSE...
            </div>
          )}
          {visibleItems >= trace.length && (
            <div className="text-green-500/80 text-[10px] mt-3 pt-3 border-t border-green-900/30 flex items-center gap-1.5 animate-in fade-in duration-500">
               <CheckCircle className="w-3 h-3" /> PIPELINE_EXECUTION_COMPLETE
            </div>
          )}
       </div>
    </div>
  );
}
