"use client";
import { useCallback, useState } from "react";
import { Upload, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { uploadFile } from "@/lib/api";

interface Props {
  onUploaded?: () => void;
}

export default function UploadZone({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const processFile = useCallback(async (file: File) => {
    setUploading(file.name);
    setLastResult(null);
    try {
      const res = await uploadFile(file);
      setLastResult({ ok: true, msg: `${file.name} indexed (${res.result?.chunks_added ?? "?"} chunks)` });
      onUploaded?.();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setLastResult({ ok: false, msg });
    } finally {
      setUploading(null);
    }
  }, [onUploaded]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [processFile]);

  const onInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = "";
  }, [processFile]);

  return (
    <div className="p-3">
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-2 border-2 border-dashed rounded-xl p-4 cursor-pointer transition-all text-center
          ${dragging
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 dark:border-gray-600 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-700/30"
          }`}
      >
        <input
          type="file"
          className="hidden"
          accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.csv,.txt,.md,.json"
          onChange={onInput}
        />

        {uploading ? (
          <>
            <Loader2 size={20} className="animate-spin text-blue-500" />
            <span className="text-xs text-gray-600 dark:text-gray-400 truncate w-full text-center">
              Indexing {uploading}…
            </span>
          </>
        ) : (
          <>
            <Upload size={18} className="text-gray-400" />
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Drop file or click to upload
            </span>
            <span className="text-[10px] text-gray-400">
              PDF · DOCX · PPTX · XLSX · CSV · TXT
            </span>
          </>
        )}
      </label>

      {lastResult && (
        <div className={`mt-2 flex items-start gap-1.5 text-xs rounded-lg p-2
          ${lastResult.ok
            ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
            : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
          }`}
        >
          {lastResult.ok ? <CheckCircle size={12} className="mt-0.5 flex-shrink-0" /> : <XCircle size={12} className="mt-0.5 flex-shrink-0" />}
          <span>{lastResult.msg}</span>
        </div>
      )}
    </div>
  );
}
