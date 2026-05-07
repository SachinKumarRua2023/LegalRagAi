"use client";
import { useEffect, useState, useCallback } from "react";
import { RefreshCw, FileText, Database, ChevronRight, Download, Loader2 } from "lucide-react";
import { listFiles, getStatus, triggerDownload } from "@/lib/api";
import type { IndexedFile, IndexStatus } from "@/lib/types";
import UploadZone from "./UploadZone";

const EXT_COLORS: Record<string, string> = {
  pdf:  "text-red-500",
  docx: "text-blue-500",
  doc:  "text-blue-500",
  pptx: "text-orange-500",
  xlsx: "text-green-500",
  csv:  "text-emerald-500",
  txt:  "text-gray-400",
  json: "text-yellow-500",
};

function getExt(f: string) { return f.split(".").pop()?.toLowerCase() || ""; }
function shortFolder(p: string) {
  const parts = p.replace(/\\/g, "/").split("/");
  return parts.length <= 2 ? p : parts.slice(-2).join("/");
}

interface Props {
  onFileClick?: (fileName: string) => void;
  activeFile?: string;
}

export default function Sidebar({ onFileClick, activeFile }: Props) {
  const [files, setFiles] = useState<IndexedFile[]>([]);
  const [status, setStatus] = useState<IndexStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [search, setSearch] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [f, s] = await Promise.all([listFiles(), getStatus()]);
      setFiles(f);
      setStatus(s);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await triggerDownload(20);
      setTimeout(refresh, 3000);
    } catch {}
    setDownloading(false);
  };

  const filtered = files.filter((f) =>
    !search || f.source_file.toLowerCase().includes(search.toLowerCase())
  );

  // Group by folder
  const grouped = filtered.reduce<Record<string, IndexedFile[]>>((acc, f) => {
    const folder = shortFolder(f.source_folder || "Unknown");
    (acc[folder] ??= []).push(f);
    return acc;
  }, {});

  return (
    <aside className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-200">Knowledge Base</h2>
          <button onClick={refresh} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" title="Refresh">
            <RefreshCw size={14} className={`text-gray-500 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
        {status && (
          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1"><Database size={11} />{status.total_chunks.toLocaleString()} chunks</span>
            <span className="flex items-center gap-1"><FileText size={11} />{files.length} files</span>
          </div>
        )}
      </div>

      {/* Upload zone */}
      <UploadZone onUploaded={refresh} />

      {/* Download button */}
      <div className="px-3 pb-2">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 text-xs rounded-lg bg-legal-navy text-white hover:bg-blue-800 dark:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-60 transition-colors"
        >
          {downloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          {downloading ? "Downloading data…" : "Download Legal Data"}
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2">
        <input
          type="text"
          placeholder="Search files…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-3">
        {Object.keys(grouped).length === 0 && !loading && (
          <div className="text-center py-8 text-xs text-gray-400">
            <FileText size={28} className="mx-auto mb-2 opacity-40" />
            <p>No files indexed yet.</p>
            <p className="mt-1">Upload a file or click<br />"Download Legal Data"</p>
          </div>
        )}

        {Object.entries(grouped).map(([folder, folderFiles]) => (
          <div key={folder}>
            <p className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 mb-1 truncate" title={folder}>
              {folder}
            </p>
            <ul className="space-y-0.5">
              {folderFiles.map((f) => {
                const ext = getExt(f.source_file);
                const active = activeFile === f.source_file;
                return (
                  <li key={f.source_path}>
                    <button
                      onClick={() => onFileClick?.(f.source_file)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors text-xs
                        ${active
                          ? "bg-legal-navy text-white"
                          : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                        }`}
                    >
                      <FileText size={12} className={active ? "text-legal-gold" : (EXT_COLORS[ext] || "text-gray-400")} />
                      <span className="flex-1 truncate">{f.source_file}</span>
                      {active && <ChevronRight size={10} />}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </aside>
  );
}
