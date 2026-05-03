"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, Scale, User, Loader2 } from "lucide-react";
import SourceCard from "./SourceCard";
import type { Message as MessageType } from "@/lib/types";

function timeStr(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Message({ msg }: { msg: MessageType }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = msg.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[75%]">
          <div className="bg-legal-navy text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
            {msg.content}
          </div>
          {msg.filterFile && (
            <p className="text-xs text-gray-400 mt-1 text-right">
              Filter: {msg.filterFile}
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1 text-right">{timeStr(msg.timestamp)}</p>
        </div>
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
          <User size={16} className="text-gray-600 dark:text-gray-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-legal-navy flex items-center justify-center">
        <Scale size={16} className="text-legal-gold" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3">
          {msg.isLoading ? (
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Researching legal cases…</span>
            </div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none text-gray-800 dark:text-gray-200">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources accordion */}
        {!msg.isLoading && msg.sources && msg.sources.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-legal-navy dark:hover:text-blue-400 transition-colors"
            >
              {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {msg.chunks_retrieved} chunks from {msg.sources.length} file
              {msg.sources.length !== 1 ? "s" : ""}
            </button>

            {showSources && (
              <div className="mt-2 grid gap-2">
                {msg.sources.map((src, i) => (
                  <SourceCard key={i} source={src} index={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-gray-400 mt-1">{timeStr(msg.timestamp)}</p>
      </div>
    </div>
  );
}
