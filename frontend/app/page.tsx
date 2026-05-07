"use client";
import { useState, useEffect } from "react";
import { Scale, Moon, Sun, Menu, X, Wifi, WifiOff } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";

export default function Home() {
  const [activeFile, setActiveFile] = useState<string | undefined>();
  const [dark, setDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendStatus, setBackendStatus] = useState<"unknown" | "up" | "warming">("unknown");

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved === "dark" || (!saved && prefersDark)) {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  // Wake up backend on load + keep alive every 10 min
  useEffect(() => {
    const ping = async () => {
      try {
        const res = await fetch("/api/status", { cache: "no-store" });
        setBackendStatus(res.ok ? "up" : "warming");
      } catch {
        setBackendStatus("warming");
      }
    };
    ping();
    const interval = setInterval(ping, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Top nav */}
      <header className="flex items-center gap-3 px-4 py-3 bg-legal-navy text-white border-b border-blue-900 z-10 flex-shrink-0">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1 rounded hover:bg-blue-800 transition-colors lg:hidden"
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        <div className="flex items-center gap-2">
          <Scale size={22} className="text-legal-gold" />
          <div>
            <h1 className="font-bold text-base leading-tight">Legal AI Research</h1>
            <p className="text-[10px] text-blue-300 leading-tight">US Legal Cases · RAG + Pinecone · Groq</p>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Backend status indicator */}
          {backendStatus === "warming" && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs bg-yellow-600/60 text-yellow-200 px-2.5 py-1 rounded-full animate-pulse">
              <WifiOff size={11} /> Backend warming up…
            </span>
          )}
          {backendStatus === "up" && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs bg-green-700/40 text-green-300 px-2.5 py-1 rounded-full">
              <Wifi size={11} /> Connected
            </span>
          )}

          {activeFile && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs bg-blue-800/60 text-blue-200 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              {activeFile}
            </span>
          )}
          <button
            onClick={toggleDark}
            className="p-1.5 rounded-lg hover:bg-blue-800 transition-colors"
            title="Toggle dark mode"
          >
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </header>

      {/* Warming up banner */}
      {backendStatus === "warming" && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800 px-4 py-2 text-xs text-yellow-800 dark:text-yellow-300 text-center">
          Backend is starting up (free tier cold start — ~60 seconds). Queries will work once it&apos;s ready.
        </div>
      )}

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — always mounted, hidden with CSS to avoid remount API spam */}
        <div className={`flex-shrink-0 transition-all duration-200 overflow-hidden ${sidebarOpen ? "w-64" : "w-0"}`}>
          <Sidebar
            activeFile={activeFile}
            onFileClick={(f) => setActiveFile(activeFile === f ? undefined : f)}
          />
        </div>

        {/* Main chat */}
        <main className="flex-1 overflow-hidden bg-gray-50 dark:bg-gray-950">
          <ChatWindow
            activeFile={activeFile}
            onClearFile={() => setActiveFile(undefined)}
          />
        </main>
      </div>
    </div>
  );
}
