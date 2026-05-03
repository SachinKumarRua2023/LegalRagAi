export interface Source {
  source_file: string;
  source_path: string;
  source_folder: string;
  source_citation: string;
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  query: string;
  chunks_retrieved: number;
}

export interface IndexedFile {
  source_file: string;
  source_path: string;
  source_folder: string;
  file_type: string;
  document_type?: string;
}

export interface IndexStatus {
  collection: string;
  total_chunks: number;
  unique_files: number;
  db_path: string;
  files: IndexedFile[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  chunks_retrieved?: number;
  timestamp: Date;
  isLoading?: boolean;
  filterFile?: string;
  filterFolder?: string;
  filterType?: string;
}

export type FileTypeIcon = "pdf" | "docx" | "doc" | "pptx" | "ppt" | "xlsx" | "xls" | "csv" | "txt" | "json" | "other";
