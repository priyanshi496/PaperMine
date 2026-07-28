"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { Loader2 } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await axios.post("http://localhost:8000/api/v1/auth/signup", {
        email,
        password,
        company_name: companyName
      });
      setSuccess(true);
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to create account. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-container flex flex-col md:flex-row font-sans">
      
      {/* Left side: Branding / Value Prop */}
      <div className="w-full md:w-5/12 bg-primary text-on-primary p-12 flex flex-col justify-between relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-16">
            <span className="material-symbols-outlined text-[32px] text-secondary">category</span>
            <span className="font-bold text-[24px] tracking-tight">PaperMine</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6 tracking-tight">
            Partner with us. <br/>
            <span className="text-secondary">Accelerate</span> your payments.
          </h1>
          <p className="text-on-primary-container text-lg max-w-md opacity-90 leading-relaxed font-medium">
            Join the PaperMine Vendor Network. Submit invoices digitally, track payment statuses in real-time, and get paid faster.
          </p>
        </div>
        
        <div className="relative z-10 mt-16 font-mono text-sm opacity-80 flex gap-4 text-on-primary-container">
          <span>&copy; {new Date().getFullYear()} PaperMine</span>
          <span>Terms</span>
          <span>Privacy</span>
        </div>

        {/* Decorative background element */}
        <div className="absolute -bottom-32 -right-32 w-[600px] h-[600px] bg-white opacity-5 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Right side: Signup Form */}
      <div className="w-full md:w-7/12 bg-surface flex items-center justify-center p-8 md:p-12 relative overflow-y-auto">
        
        <div className="w-full max-w-md mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
          
          <div className="text-center md:text-left space-y-2">
            <h2 className="text-3xl font-bold text-on-surface tracking-tight">Create Vendor Account</h2>
            <p className="text-on-surface-variant text-[15px]">Fill in your details below to get started.</p>
          </div>

          {success ? (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-6 rounded-xl flex flex-col items-center justify-center text-center space-y-4">
              <span className="material-symbols-outlined text-4xl text-emerald-500">check_circle</span>
              <div>
                <h3 className="font-bold text-lg mb-1">Account Created!</h3>
                <p className="text-sm opacity-80">You will be redirected to login shortly.</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSignup} className="space-y-5">
              
              <div className="space-y-1.5">
                <label className="text-[13px] font-bold text-on-surface-variant">Company Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-[20px] text-on-surface-variant/50">storefront</span>
                  </div>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="block w-full pl-10 pr-3 py-3 bg-surface-container-low border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all text-on-surface text-[15px]"
                    placeholder="Acme Corp"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-bold text-on-surface-variant">Email Address</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-[20px] text-on-surface-variant/50">mail</span>
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-10 pr-3 py-3 bg-surface-container-low border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all text-on-surface text-[15px]"
                    placeholder="billing@acmecorp.com"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-bold text-on-surface-variant">Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-[20px] text-on-surface-variant/50">lock</span>
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full pl-10 pr-3 py-3 bg-surface-container-low border border-outline-variant rounded-xl focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all text-on-surface text-[15px]"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-error-container text-error p-3 rounded-lg text-[13px] font-medium flex items-start gap-2">
                  <span className="material-symbols-outlined text-[18px]">error</span>
                  <p className="mt-0.5">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-3.5 px-4 border border-transparent rounded-xl shadow-sm text-[15px] font-bold text-on-primary bg-primary hover:bg-on-primary-fixed-variant focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-all disabled:opacity-70 disabled:cursor-not-allowed mt-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Sign Up"}
              </button>
            </form>
          )}

          <div className="text-center md:text-left text-[14px] text-on-surface-variant font-medium">
            Already have an account?{" "}
            <Link href="/login" className="text-primary font-bold hover:underline underline-offset-4">
              Sign in
            </Link>
          </div>
          
        </div>
      </div>
    </div>
  );
}
