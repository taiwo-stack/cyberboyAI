"use client";

import { useState } from "react";
import { 
  ChevronDown, ChevronUp, Bot, Database, Brain, Zap, Shield, 
  Eye, Lock, Link, Activity, Fingerprint, Info
} from "lucide-react";
import { VerdictResponse } from "@/lib/api";

export default function DeepEvidence({ verdict }: { verdict: VerdictResponse }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!verdict.behavior_result && !verdict.ml_result) return null;

  const behavior = verdict.behavior_result;
  const ml = verdict.ml_result;

  return (
    <div className="w-full mt-4 animate-in fade-in slide-in-from-top-2 duration-500">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-[10px] font-bold text-slate-500 hover:text-blue-400 transition-colors uppercase tracking-[0.2em]"
      >
        {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        Technical Deep-Dive & Evidence
      </button>

      {isOpen && (
        <div className="mt-3 space-y-4 bg-[#020617] border border-slate-800/50 rounded-xl p-4 font-mono">
          
          {/* 1. Network & SSL Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* SSL Info */}
            <div className="space-y-2">
              <h5 className="text-[10px] text-blue-400/60 uppercase flex items-center gap-2">
                <Lock className="w-3 h-3" /> SSL_SECURITY_CERT
              </h5>
              <div className="bg-[#050d1a] border border-slate-800 rounded-lg p-3 space-y-1.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-500">Issuer:</span>
                  <span className="text-slate-200">{behavior?.ssl_issuer || "Unknown"}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-500">Validity:</span>
                  <span className={behavior?.dynamic_findings?.days_to_expire < 30 ? "text-amber-400" : "text-emerald-400"}>
                    {behavior?.dynamic_findings?.days_to_expire || 0} days remaining
                  </span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-500">Cert Age:</span>
                  <span className={behavior?.dynamic_findings?.cert_age_days < 14 ? "text-red-400" : "text-slate-300"}>
                    {behavior?.dynamic_findings?.cert_age_days || 0} days old
                  </span>
                </div>
              </div>
            </div>

            {/* Redirect Hops */}
            <div className="space-y-2">
              <h5 className="text-[10px] text-purple-400/60 uppercase flex items-center gap-2">
                <Link className="w-3 h-3" /> REDIRECT_CHAIN
              </h5>
              <div className="bg-[#050d1a] border border-slate-800 rounded-lg p-3">
                <div className="space-y-2 max-h-32 overflow-y-auto pr-2 scrollbar-hide">
                  {behavior?.redirect_chain?.map((url: string, i: number) => (
                    <div key={i} className="flex gap-2 items-start text-[10px]">
                      <span className="text-slate-600 font-bold">#{i+1}</span>
                      <span className="text-slate-400 truncate break-all opacity-80 hover:opacity-100 transition-opacity">
                        {url}
                      </span>
                    </div>
                  ))}
                  {(!behavior?.redirect_chain || behavior.redirect_chain.length === 1) && (
                    <div className="text-slate-600 text-[10px] italic italic">No redirects detected. Direct connection.</div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 2. ML Feature Matrix */}
          {ml?.features && (
            <div className="space-y-2">
              <h5 className="text-[10px] text-emerald-400/60 uppercase flex items-center gap-2">
                <Fingerprint className="w-3 h-3" /> HEURISTIC_FEATURE_MATRIX
              </h5>
              <div className="bg-[#050d1a] border border-slate-800 rounded-lg p-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2">
                  {Object.entries(ml.features).slice(0, 12).map(([key, val]: [string, any]) => (
                    <div key={key} className="flex justify-between items-center border-b border-white/5 pb-1">
                      <span className="text-[9px] text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-slate-300 font-bold">
                        {typeof val === 'number' ? val.toFixed(2) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[9px] text-slate-600 italic">
                  * ML vectors represent normalized structural patterns used by the RandomForest ensemble.
                </p>
              </div>
            </div>
          )}

          {/* 3. Behavioral Findings */}
          {behavior?.dynamic_findings && (
            <div className="space-y-2">
              <h5 className="text-[10px] text-pink-400/60 uppercase flex items-center gap-2">
                <Activity className="w-3 h-3" /> DYNAMIC_OBSERVATIONS
              </h5>
              <div className="grid grid-cols-1 gap-2">
                {behavior.dynamic_findings.evidence?.map((e: string, i: number) => (
                  <div key={i} className="flex gap-3 bg-red-950/20 border border-red-900/30 rounded-lg p-2.5 items-center">
                    <Info className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    <span className="text-[11px] text-red-200/80">{e}</span>
                  </div>
                ))}
                {(!behavior.dynamic_findings.evidence || behavior.dynamic_findings.evidence.length === 0) && (
                  <div className="text-slate-600 text-[10px] p-2 bg-slate-900/30 rounded border border-white/5 italic">
                    No anomalous dynamic behaviors observed during Playwright simulation.
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
