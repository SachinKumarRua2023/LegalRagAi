import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legal AI Research — CompleteRagAI",
  description: "AI-powered US legal case research with RAG + ChromaDB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
