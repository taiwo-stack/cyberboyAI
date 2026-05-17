import { AlertTriangle, CheckCircle, Flame, ShieldAlert } from "lucide-react";
import { VerdictResponse } from "@/lib/api";

export default function VerdictCard({ verdict }: { verdict: VerdictResponse }) {
  const isSafe = verdict.verdict === "SAFE";
  const isSuspicious = verdict.verdict === "SUSPICIOUS";
  const isDangerous = verdict.verdict === "DANGEROUS";

  let headerColor = "bg-green-600/10 border-green-500/20 text-green-400";
  let barColor = "bg-green-500";
  let icon = <CheckCircle className="h-10 w-10 text-green-500" />;

  if (isSuspicious) {
    headerColor = "bg-amber-500/10 border-amber-500/20 text-amber-500";
    barColor = "bg-amber-500";
    icon = <AlertTriangle className="h-10 w-10 text-amber-500" />;
  } else if (isDangerous) {
    headerColor = "bg-red-500/10 border-red-500/20 text-red-500";
    barColor = "bg-red-500";
    icon = <ShieldAlert className="h-10 w-10 text-red-500" />;
  }

  // The backend returns a rigid Threat Score (0.0 to 1.0).
  // For the UI, "Confidence" should reflect certainty in the specific verdict.
  const threatPercentage = Math.round(verdict.score * 100);
  let displayConfidence = threatPercentage;
  
  // If the system declares it SAFE, a lower threat percentage equals HIGHER confidence it is safe.
  if (isSafe) {
    displayConfidence = 100 - threatPercentage;
  }

  return (
    <div className="w-full max-w-3xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        {/* Header Block */}
        <div className={`p-6 border-b flex items-center gap-4 ${headerColor}`}>
          {icon}
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-3xl font-black uppercase tracking-wider">{verdict.verdict}</h2>
              {verdict.threat_type && (
                <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.1em] bg-white/10 text-white border border-white/20 backdrop-blur-md shadow-lg flex items-center gap-1.5">
                  <span className="opacity-50">Type:</span>
                  <span>{verdict.threat_type}</span>
                </span>
              )}
            </div>
            <p className="opacity-80 font-medium mt-1">Confidence Score: {displayConfidence}%</p>
          </div>
        </div>

        {/* Score Bar */}
        <div className="h-1.5 w-full bg-slate-800">
          <div 
            className={`h-full ${barColor} transition-all duration-1000 ease-out`} 
            style={{ width: `${displayConfidence}%` }} 
          />
        </div>

        {/* Content Block */}
        <div className="p-6 md:p-8 space-y-6">
          <div className="text-slate-300 text-lg leading-relaxed">
            {verdict.explanation}
          </div>

          {verdict.red_flags.length > 0 && (
            <div className="bg-slate-950 rounded-xl p-5 border border-slate-800">
              <h3 className="text-slate-400 font-semibold mb-3 flex items-center gap-2 text-sm uppercase tracking-wider">
                <Flame className="h-4 w-4 text-orange-500" />
                Detected Threat Signals
              </h3>
              <ul className="space-y-2">
                {verdict.red_flags.map((flag, idx) => (
                  <li key={idx} className="flex items-start gap-3 text-slate-300">
                    <span className="text-slate-600 mt-1">•</span>
                    <span className="leading-snug">{flag}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Advice Box */}
          <div className="bg-blue-900/20 border border-blue-500/20 rounded-xl p-5">
            <h3 className="text-blue-400 font-semibold mb-1 text-sm uppercase tracking-wider">Actionable Advice</h3>
            <p className="text-blue-100/80">{verdict.advice}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
