"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, X, Filter, Scale } from "lucide-react";
import Message from "./Message";
import { sendQuery } from "@/lib/api";
import type { Message as MessageType } from "@/lib/types";

let idCounter = 0;
function nextId() { return String(++idCounter); }

interface Props {
  activeFile?: string;
  onClearFile?: () => void;
}

const SUGGESTIONS = [
  "What are the key elements of a contract breach case?",
  "Explain Fourth Amendment search and seizure rights",
  "What factors determine civil rights violations under Section 1983?",
  "How do courts determine negligence in personal injury cases?",
  "What is the burden of proof in employment discrimination claims?",
];

export default function ChatWindow({ activeFile, onClearFile }: Props) {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = useCallback(async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: MessageType = {
      id: nextId(),
      role: "user",
      content: question,
      timestamp: new Date(),
      filterFile: activeFile,
      filterType: filterType || undefined,
    };

    const loadingMsg: MessageType = {
      id: nextId(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput("");
    setLoading(true);

    const MAX_RETRIES = 3;
    const RETRY_SEC = 20;

    const updateLoading = (text: string) =>
      setMessages((prev) =>
        prev.map((m) => (m.id === loadingMsg.id ? { ...m, content: text } : m))
      );

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      if (attempt > 0) {
        for (let t = RETRY_SEC; t > 0; t--) {
          updateLoading(`Backend warming up — retrying in ${t}s…`);
          await new Promise<void>((r) => setTimeout(r, 1000));
        }
        updateLoading(`Retrying… (attempt ${attempt}/${MAX_RETRIES})`);
      }

      try {
        const res = await sendQuery(question, {
          filter_file: activeFile || undefined,
          filter_file_type: filterType || undefined,
        });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, content: res.answer, sources: res.sources, chunks_retrieved: res.chunks_retrieved, isLoading: false }
              : m
          )
        );
        break;
      } catch (e: unknown) {
        const errMsg = e instanceof Error ? e.message : String(e);
        const isWarmup = errMsg.includes("starting up") || errMsg.includes("warming") || errMsg.includes("503");
        if (isWarmup && attempt < MAX_RETRIES) continue;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id ? { ...m, content: `Error: ${errMsg}`, isLoading: false } : m
          )
        );
        break;
      }
    }

    setLoading(false);
  }, [loading, activeFile, filterType]);

  return (
    <div className="flex flex-col h-full">
      {/* Active filter bar */}
      {(activeFile || filterType) && (
        <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 text-xs">
          <Filter size={12} className="text-blue-500" />
          {activeFile && (
            <span className="flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
              {activeFile}
              <button onClick={onClearFile} className="ml-1 hover:text-red-500 transition-colors"><X size={10} /></button>
            </span>
          )}
          {filterType && (
            <span className="flex items-center gap-1 bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded-full">
              Only .{filterType}
              <button onClick={() => setFilterType("")} className="ml-1 hover:text-red-500"><X size={10} /></button>
            </span>
          )}
          <span className="text-gray-500 ml-auto">Searching within filter</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-legal-navy flex items-center justify-center">
              <Scale size={32} className="text-legal-gold" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Legal AI Research</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Ask anything about US legal cases. Upload your files or download case data.
              </p>
            </div>
            <div className="grid gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => submit(s)}
                  className="text-left px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <Message key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        {/* File type filter chips */}
        <div className="flex items-center gap-1.5 mb-2 flex-wrap">
          <span className="text-xs text-gray-400">Filter:</span>
          {["pdf", "docx", "pptx", "xlsx", "csv", "txt"].map((ext) => (
            <button
              key={ext}
              onClick={() => setFilterType(filterType === ext ? "" : ext)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors
                ${filterType === ext
                  ? "bg-legal-navy border-legal-navy text-white"
                  : "border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-blue-400"
                }`}
            >
              .{ext}
            </button>
          ))}
        </div>

        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(input);
              }
            }}
            placeholder={
              activeFile
                ? `Ask about ${activeFile}…`
                : "Ask about US legal cases… (Enter to send, Shift+Enter for new line)"
            }
            className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-legal-navy dark:focus:ring-blue-500"
          />
          <button
            onClick={() => submit(input)}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-legal-navy text-white flex items-center justify-center hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5">
          Click a file in the sidebar to search within that file only.
        </p>
      </div>
    </div>
  );
}
