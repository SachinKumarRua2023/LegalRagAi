"use client";
import { FileText, Folder, BookOpen, Hash } from "lucide-react";
import type { Source } from "@/lib/types";

const FILE_COLORS: Record<string, string> = {
  pdf: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  docx: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  doc:  "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  pptx: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  xlsx: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  csv:  "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  txt:  "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  json: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
};

function getExt(filename: string) {
  return filename.split(".").pop()?.toLowerCase() || "txt";
}

function shortPath(p: string) {
  if (!p) return "";
  const parts = p.replace(/\\/g, "/").split("/");
  if (parts.length <= 3) return p;
  return "…/" + parts.slice(-2).join("/");
}

export default function SourceCard({ source, index }: { source: Source; index: number }) {
  const ext = getExt(source.source_file);
  const colorClass = FILE_COLORS[ext] || FILE_COLORS.txt;
  const score = Math.round(source.relevance_score * 100);

  // Parse citation parts from "File: x | Page 3 | Section: y"
  const parts = source.source_citation.split("|").map((s) => s.trim());

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm hover:border-blue-300 dark:hover:border-blue-600 transition-colors">
      {/* Index badge */}
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-legal-navy dark:bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
        {index}
      </div>

      <div className="flex-1 min-w-0">
        {/* File name + type badge */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]">
            {source.source_file}
          </span>
          <span className={`px-1.5 py-0.5 rounded text-xs font-semibold uppercase ${colorClass}`}>
            {ext}
          </span>
          <span className="ml-auto text-xs text-gray-400 flex items-center gap-1">
            <Hash size={10} /> {score}%
          </span>
        </div>

        {/* Folder */}
        {source.source_folder && (
          <div className="flex items-center gap-1 mt-1 text-gray-500 dark:text-gray-400">
            <Folder size={12} />
            <span className="truncate text-xs">{shortPath(source.source_folder)}</span>
          </div>
        )}

        {/* Citation detail parts (page, section) */}
        {parts.length > 1 && (
          <div className="flex items-center gap-1 mt-1 text-gray-500 dark:text-gray-400">
            <BookOpen size={12} />
            <span className="text-xs">{parts.slice(1).join(" · ")}</span>
          </div>
        )}
      </div>
    </div>
  );
}
