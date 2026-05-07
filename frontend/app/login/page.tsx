"use client";
import { useState, useEffect } from "react";
import { Scale, Lock, User } from "lucide-react";
import { loginUser, getStoredUser } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getStoredUser()) router.replace("/");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await loginUser(username.trim(), password);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a1628] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-[#c9a84c] rounded-full flex items-center justify-center mb-4 shadow-lg">
            <Scale className="w-8 h-8 text-[#0a1628]" />
          </div>
          <h1 className="text-2xl font-bold text-white">Legal AI Research</h1>
          <p className="text-[#8fa0b8] text-sm mt-1">RAG · Pinecone · Groq</p>
        </div>

        {/* Card */}
        <div className="bg-[#112240] border border-[#1e3a5f] rounded-xl p-8 shadow-2xl">
          <h2 className="text-white font-semibold text-lg mb-6 text-center">Sign in to continue</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[#8fa0b8] text-sm mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8fa0b8]" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#0a1628] border border-[#1e3a5f] rounded-lg pl-10 pr-4 py-2.5 text-white placeholder-[#4a6080] focus:outline-none focus:border-[#c9a84c] transition-colors"
                  placeholder="Enter username"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label className="block text-[#8fa0b8] text-sm mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8fa0b8]" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#0a1628] border border-[#1e3a5f] rounded-lg pl-10 pr-4 py-2.5 text-white placeholder-[#4a6080] focus:outline-none focus:border-[#c9a84c] transition-colors"
                  placeholder="Enter password"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-2.5 text-red-300 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#c9a84c] hover:bg-[#b8973b] disabled:opacity-60 disabled:cursor-not-allowed text-[#0a1628] font-semibold rounded-lg py-2.5 transition-colors mt-2"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
