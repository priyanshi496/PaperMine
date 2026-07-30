"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await axios.post("http://localhost:8000/api/v1/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      });

      login(res.data.access_token, res.data.user);
      router.push("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to login. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-outline-variant p-8">
        
        <div className="text-center mb-10">
          <h1 className="font-sans text-[28px] font-bold text-on-surface mb-2 tracking-tight">PaperMine</h1>
          <p className="font-mono text-[12px] text-on-surface-variant uppercase tracking-widest">Financial Intelligence</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="bg-error-container text-error px-4 py-3 rounded-lg text-sm font-medium border border-error/20 flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">error</span>
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="font-mono text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Email Address</label>
            <input 
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-lg focus:ring-2 focus:ring-secondary focus:border-secondary transition-all outline-none text-sm font-medium"
              placeholder="admin@papermine.com"
            />
          </div>

          <div className="space-y-2">
            <label className="font-mono text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Password</label>
            <input 
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-lg focus:ring-2 focus:ring-secondary focus:border-secondary transition-all outline-none text-sm font-medium"
              placeholder="••••••••"
            />
          </div>

          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-on-primary font-bold py-3.5 rounded-lg hover:bg-on-primary-fixed-variant transition-colors disabled:opacity-70 flex justify-center items-center gap-2 mt-4"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Sign In"}
          </button>
        </form>

        <div className="text-center text-[14px] text-on-surface-variant font-medium mt-6">
          Don't have an account?{" "}
          <Link href="/signup" className="text-primary font-bold hover:underline underline-offset-4">
            Sign up as Vendor
          </Link>
        </div>

        <div className="mt-8 border-t border-outline-variant pt-6 text-center">
            <p className="text-[11px] font-mono text-on-surface-variant mb-2">TEST ACCOUNTS</p>
            <div className="text-[12px] text-on-surface-variant space-y-1 bg-surface-container-low p-3 rounded text-left font-mono">
                <p>CFO: cfo@technova.com / cfo123</p>
                <p>Finance Team: finance@technova.com / finance123</p>
                <p>Vendor: onebitehapoli@vendor.com / vendor123</p>
            </div>
        </div>

      </div>
    </div>
  );
}
