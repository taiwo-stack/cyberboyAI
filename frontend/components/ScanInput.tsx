"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";

type ScanInputProps = {
  onSubmit: (input: string) => void;
  loading: boolean;
};

export default function ScanInput({ onSubmit, loading }: ScanInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSubmit(inputValue.trim());
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto mt-8 px-4">
      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-6 w-6 text-slate-500 group-focus-within:text-blue-500 transition-colors" />
        </div>
        <input
          type="text"
          className="w-full bg-slate-900 border-2 border-slate-700 text-slate-100 rounded-full py-4 pl-12 pr-32 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-xl transition-all transition-colors placeholder:text-slate-500 text-lg"
          placeholder="Paste a suspicious link, email text, or SMS message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={loading}
          autoComplete="off"
        />
        <div className="absolute inset-y-2 right-2 flex items-center">
          <button
            type="submit"
            disabled={!inputValue.trim() || loading}
            className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 px-6 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Scanning...
              </>
            ) : (
              "Scan Now"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
