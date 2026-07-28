"use client";

import InsightsFeed from "@/components/InsightsFeed";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

interface Priority {
  icon: string;
  message: string;
  severity: string;
}

interface DashboardData {
  docs_analyzed: number;
  priorities: Priority[];
  high_risk_count: number;
  unresolved_alerts_count: number;
}

export default function Home() {
  const { authState } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/dashboard/daily-brief");
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (!mounted || !authState.user) return null;

  return (
    <div className="pt-16 min-h-screen p-8 max-w-[1600px] mx-auto animate-in fade-in duration-500">
      
      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-6">
        
        {/* Intelligence Overview - The AI Daily Brief */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
          
          <div className="bg-white border border-outline-variant p-8 rounded-2xl shadow-sm flex flex-col h-[700px]">
            <h1 className="font-sans text-[36px] font-bold text-on-surface leading-[44px] tracking-[-0.02em] mb-4">
              Good Morning!
            </h1>
            
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-6 bg-slate-100 rounded w-1/2"></div>
                <div className="h-4 bg-slate-100 rounded w-3/4"></div>
                <div className="h-4 bg-slate-100 rounded w-2/3"></div>
              </div>
            ) : data ? (
              <>
                <p className="font-mono text-[16px] text-on-surface-variant mb-8">
                  I analyzed {data.docs_analyzed} documents overnight.
                  <br />
                  Here are today's priorities:
                </p>

                <div className="space-y-4 flex-1">
                  {data.priorities.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-4 p-4 rounded-xl hover:bg-slate-50 transition-colors">
                      <div className="text-2xl mt-0.5">{item.icon}</div>
                      <p className="font-sans text-[16px] font-medium text-on-surface">{item.message}</p>
                    </div>
                  ))}
                  
                  {data.priorities.length === 0 && (
                    <div className="text-slate-400 p-4">No critical priorities today.</div>
                  )}
                </div>

                <div className="mt-8 pt-8 border-t border-slate-100 grid grid-cols-2 gap-4">
                  <div className="bg-error-container/30 p-4 rounded-xl border border-error/10 flex flex-col">
                    <span className="font-mono text-[12px] font-medium text-error uppercase tracking-wider mb-1">Needs Approval</span>
                    <span className="font-sans text-[28px] font-bold text-error">{data.high_risk_count}</span>
                    <span className="font-sans text-[12px] text-error/80 mt-1">High-Risk Invoices</span>
                  </div>
                  <div className="bg-secondary-container/30 p-4 rounded-xl border border-secondary/10 flex flex-col">
                    <span className="font-mono text-[12px] font-medium text-secondary uppercase tracking-wider mb-1">Active Anomalies</span>
                    <span className="font-sans text-[28px] font-bold text-secondary">{data.unresolved_alerts_count}</span>
                    <span className="font-sans text-[12px] text-secondary/80 mt-1">Pending alerts in Action Center</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-slate-400">Failed to load daily brief.</div>
            )}
          </div>
          
        </div>

        {/* Action Center / InsightsFeed Widget */}
        <div className="col-span-12 lg:col-span-4 flex flex-col h-[700px]">
          <InsightsFeed />
        </div>
        
      </div>

    </div>
  );
}
