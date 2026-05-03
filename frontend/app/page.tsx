"use client";
import { useState } from "react";
import { Scale, Moon, Sun, Menu, X } from "lucide-react";
import { useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";

export default function Home() {
  const [activeFile, setActiveFile] = useState<string | undefined>();
  const [dark, setDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved === "dark" || (!saved && prefersDark)) {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
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
            <p className="text-[10px] text-blue-300 leading-tight">US Legal Cases · RAG + ChromaDB · Groq / Gemini / Claude</p>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
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

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className={`
          flex-shrink-0 transition-all duration-200 overflow-hidden
          ${sidebarOpen ? "w-64" : "w-0"}
        `}>
          {sidebarOpen && (
            <Sidebar
              activeFile={activeFile}
              onFileClick={(f) => setActiveFile(activeFile === f ? undefined : f)}
            />
          )}
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
