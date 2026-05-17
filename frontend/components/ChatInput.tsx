"use client";

import { useState, useRef } from "react";
import { ArrowUp, Loader2, ImagePlus, X } from "lucide-react";

type ChatInputProps = {
  onSubmit: (input: string, imageBase64?: string) => void;
  loading: boolean;
};

export default function ChatInput({ onSubmit, loading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [imageBase64, setImageBase64] = useState<string | undefined>();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const processFile = (file: File) => {
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setImageBase64(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() || imageBase64) {
      onSubmit(inputValue.trim() || "Analyze this screenshot", imageBase64);
      setInputValue("");
      setImageBase64(undefined);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 md:p-6 fade-in">
      <form 
        onSubmit={handleSubmit} 
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative group flex flex-col bg-[#131b2c] border rounded-2xl shadow-xl overflow-hidden transition-all ${isDragging ? 'border-blue-500 bg-[#162038]' : 'border-slate-700/50 focus-within:ring-1 focus-within:ring-blue-500/50'}`}
      >
        {imageBase64 && (
          <div className="relative p-4 pb-0">
            <div className="relative inline-block">
              <img src={imageBase64} alt="Upload preview" className="h-16 w-16 object-cover rounded-lg border border-blue-500/50 shadow-md" />
              <button 
                type="button" 
                onClick={() => setImageBase64(undefined)}
                className="absolute -top-2 -right-2 bg-slate-800 text-slate-300 hover:text-white rounded-full p-1 border border-slate-600 hover:bg-red-500 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}

        <div className="flex items-end">
          <div className="p-4 flex flex-col items-center justify-center shrink-0">
            <input 
              type="file" 
              accept="image/*" 
              className="hidden" 
              ref={fileInputRef}
              onChange={handleFileSelect}
            />
            <button 
              type="button" 
              onClick={() => fileInputRef.current?.click()}
              className="p-1 rounded-full text-slate-400 hover:text-blue-400 hover:bg-slate-800 transition-colors"
              title="Upload Screenshot"
            >
              <ImagePlus className="w-5 h-5" />
            </button>
          </div>

          <textarea
            rows={1}
            className="w-full bg-transparent text-slate-100 py-4 px-2 focus:outline-none resize-none max-h-32 placeholder:text-slate-500 placeholder:font-normal font-medium leading-relaxed"
            placeholder="Send a phishing link, suspicious SMS, or drop a screenshot..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            autoComplete="off"
          />

          <div className="p-3 shrink-0 flex items-center justify-center">
            <button
              type="submit"
              disabled={(!inputValue.trim() && !imageBase64) || loading}
              className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <ArrowUp className="w-5 h-5 stroke-[2.5]" />
              )}
            </button>
          </div>
        </div>
      </form>
      <div className="text-center mt-2 text-xs text-slate-500 font-medium">
        CyberBoyAI can make mistakes. Consider checking important links directly with the issuing organization.
      </div>
    </div>
  );
}
