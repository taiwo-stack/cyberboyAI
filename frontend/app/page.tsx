"use client";

import { useEffect, useState, useRef } from "react";
import { ShieldCheck, Plus, History, Loader2, Shield } from "lucide-react";
import ChatInput from "@/components/ChatInput";
import ChatBubble from "@/components/ChatBubble";
import { analyzeInput, VerdictResponse } from "@/lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "ai";
  content?: string;
  verdictData?: VerdictResponse;
};

type HistoryItem = {
  id: string;
  url: string;
  verdict: string;
  timestamp: string;
};

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const bottomRef = useRef<HTMLDivElement>(null);

  // Initialize App
  useEffect(() => {
    // Welcome Message
    setMessages([
      {
        id: "msg-welcome",
        role: "ai",
        content: "System online. I am **GaudOn**, your dedicated multi-agent cybersecurity sentry.\n\nDrop a suspicious screenshot, forward a deceptive email, or paste a malicious URL below. I will instantly tear the threat apart using my 9-Layer Defense-in-Depth pipeline—analyzing everything from linguistic intent and structural machine learning down to the live execution code.",
      }
    ]);

    // Load Local History for LinkedIn Demo effect
    const savedHistory = localStorage.getItem("cyberboy_history");
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch (e) {}
    }
  }, []);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleScan = async (input: string, imageBase64?: string) => {
    setLoading(true);
    setError(null);

    // 1. Add User Input to Chat
    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);

    try {
      // 2. Fetch Analysis
      const result = await analyzeInput(input, imageBase64);
      
      // 3. Add AI Verdict Bubble
      let aiMsg: ChatMessage;
      if (result.verdict === "GREETING") {
        aiMsg = { id: (Date.now() + 1).toString(), role: "ai", content: result.explanation };
      } else {
        aiMsg = { id: (Date.now() + 1).toString(), role: "ai", verdictData: result };
      }
      setMessages((prev) => [...prev, aiMsg]);

      // 4. Save to History (if suspicious or dangerous)
      if (result.verdict !== "SAFE") {
        const newHist: HistoryItem = {
          id: (Date.now() + 2).toString(),
          url: input,
          verdict: result.verdict,
          timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        };
        const updatedHistory = [newHist, ...history].slice(0, 15); // keep last 15
        setHistory(updatedHistory);
        localStorage.setItem("cyberboy_history", JSON.stringify(updatedHistory));
      }

    } catch (err: any) {
      setError(err.message || "Failed to analyze input. Ensure the backend is active.");
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: "ai", content: `**Error:** ${err.message || "Could not connect to the GaudOn backend pipeline."}` }]);
    } finally {
      setLoading(false);
    }
  };

  const startNewScan = () => {
    setMessages([
      {
        id: "msg-welcome-2",
        role: "ai",
        content: "What else would you like me to analyze today? Paste another threat.",
      }
    ]);
  };

  return (
    <div className="flex h-screen bg-[#000000] text-slate-100 font-sans selection:bg-blue-500/30 overflow-hidden">
      
      {/* LEFT SIDEBAR (History) */}
      <aside className="w-72 bg-[#050912] border-r border-slate-800/80 hidden md:flex flex-col shrink-0">
        
        <div className="p-4 border-b border-white/5 flex items-center gap-3">
          <div className="bg-blue-600 rounded-lg p-2 shadow-[0_0_15px_rgba(37,99,235,0.4)]">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-blue-100 to-slate-400 bg-clip-text text-transparent">
            GaudOn
          </h1>
        </div>

        <div className="p-3">
          <button 
            onClick={startNewScan}
            className="w-full flex items-center gap-3 bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 px-4 rounded-xl transition-all"
          >
            <Plus className="w-5 h-5" />
            New Analysis
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {history.length > 0 ? (
            <>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest pl-2 mb-3 mt-4">
                Threat History
              </div>
              {history.map((h) => (
                <button 
                  key={h.id} 
                  onClick={() => handleScan(h.url)}
                  className="w-full text-left bg-slate-900/50 hover:bg-slate-800/80 border border-transparent hover:border-slate-700/50 p-3 rounded-xl transition-all flex flex-col gap-1.5 focus:outline-none"
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${h.verdict === 'DANGEROUS' ? 'bg-red-500/20 text-red-500' : h.verdict === 'INVALID DOMAIN' ? 'bg-slate-500/20 text-slate-400' : 'bg-amber-500/20 text-amber-500'}`}>
                      {h.verdict}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{h.timestamp}</span>
                  </div>
                  <span className="text-sm text-slate-300 truncate w-full">{h.url}</span>
                </button>
              ))}
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-3 opacity-50 px-4 text-center mt-20">
              <History className="w-10 h-10" />
              <p className="text-sm">No threats analyzed yet.<br/>Your history will appear here.</p>
            </div>
          )}
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <main className="flex-1 flex flex-col relative h-full bg-[#030712]">
        
        {/* Mobile Header */}
        <header className="md:hidden flex items-center gap-3 p-4 border-b border-white/5 bg-[#050912]">
          <div className="bg-blue-600 rounded-md p-1.5 shadow-[0_0_15px_rgba(37,99,235,0.4)]">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <h1 className="font-bold tracking-tight text-slate-200">GaudOn</h1>
        </header>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-8 scroll-smooth pb-40">
          <div className="max-w-4xl mx-auto flex flex-col w-full">
            {messages.map((msg) => (
              <ChatBubble key={msg.id} role={msg.role} content={msg.content} verdictData={msg.verdictData} onRetry={msg.role === "user" ? handleScan : undefined} />
            ))}
            
            {loading && (
              <div className="flex justify-start mb-8 w-full fade-in">
                <div className="flex gap-4 max-w-2xl w-full items-center">
                  <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  </div>
                  <div className="text-slate-400 font-medium animate-pulse text-sm">
                    Interrogating domain across mult-agent cluster...
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} className="h-10" />
          </div>
        </div>

        {/* Input Bar pinned to bottom */}
        <div className="absolute bottom-0 left-0 right-0 w-full bg-gradient-to-t from-[#030712] via-[#030712] to-transparent pt-10 pb-6 px-4 shrink-0">
          <ChatInput onSubmit={handleScan} loading={loading} />
        </div>

      </main>

    </div>
  );
}
