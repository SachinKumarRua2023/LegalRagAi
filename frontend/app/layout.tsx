import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legal AI Research",
  description: "AI-powered US legal case research with RAG + Pinecone + Groq",
  icons: { icon: "/icon.svg" },
};

const SUPPORT_EMAIL = "seekhowithrua@gmail.com";
const SUPPORT_PHONE = "+91 88267 76018";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 antialiased flex flex-col min-h-screen">
        <div className="flex-1">
          {children}
        </div>
        {/* Support footer */}
        <footer className="bg-[#0a1628] border-t border-[#1e3a5f] py-2 px-4 flex flex-wrap items-center justify-center gap-4 text-[11px] text-[#8fa0b8]">
          <span>Need help?</span>
          <a
            href={`mailto:${SUPPORT_EMAIL}?subject=Bug Report / Support`}
            className="flex items-center gap-1 hover:text-[#c9a84c] transition-colors"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            {SUPPORT_EMAIL}
          </a>
          <span className="text-[#1e3a5f]">|</span>
          <a
            href={`tel:${SUPPORT_PHONE.replace(/\s/g, "")}`}
            className="flex items-center gap-1 hover:text-[#c9a84c] transition-colors"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            {SUPPORT_PHONE}
          </a>
          <span className="text-[#1e3a5f]">|</span>
          <span>Report bugs or issues via email</span>
        </footer>
      </body>
    </html>
  );
}
