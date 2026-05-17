"use client";

import { useEffect, useState } from "react";

export default function RiskGauge({ score, verdict }: { score: number; verdict: string }) {
  const [fill, setFill] = useState(0);

  useEffect(() => {
    // Animate the gauge from 0 to target score
    const timer = setTimeout(() => {
      setFill(score * 100);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  // Determine colors based on verdict
  let strokeColor = "stroke-blue-500";
  let filterColor = "drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]";
  
  if (verdict === "SAFE") {
    strokeColor = "stroke-green-500";
    filterColor = "drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]";
  } else if (verdict === "SUSPICIOUS") {
    strokeColor = "stroke-amber-500";
    filterColor = "drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]";
  } else if (verdict === "DANGEROUS") {
    strokeColor = "stroke-red-500";
    filterColor = "drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]";
  } else if (verdict === "INVALID DOMAIN") {
    strokeColor = "stroke-slate-500";
    filterColor = "drop-shadow-[0_0_8px_rgba(100,116,139,0.5)]";
  }

  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (fill / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center w-14 h-14 shrink-0">
      {/* Background Track */}
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="28"
          cy="28"
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="transparent"
          className="text-slate-800"
        />
        {/* Animated Fill Track */}
        <circle
          cx="28"
          cy="28"
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={`${strokeColor} ${filterColor} transition-all duration-1000 ease-out`}
          strokeLinecap="round"
        />
      </svg>
      {/* Percentage Text */}
      <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold text-slate-300">
        {Math.round(fill)}%
      </div>
    </div>
  );
}
