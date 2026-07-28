"use client";

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, BellRing, CopyCheck, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface Alert {
  id: number;
  document_id: number;
  alert_type: string;
  severity: string;
  message: string;
  explanation?: string;
  confidence_score?: number;
  resolved: boolean;
  created_at: string;
}

export default function InsightsFeed() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/insights");
      setAlerts(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const resolveAlert = async (id: number) => {
    await axios.post(`http://localhost:8000/api/v1/insights/${id}/resolve`);
    setAlerts(alerts.map(a => a.id === id ? { ...a, resolved: true } : a));
  };

  const getIcon = (type: string) => {
    if (type === "Fraud") return <ShieldAlert className="w-5 h-5 text-rose-500" />;
    if (type === "Duplicate") return <CopyCheck className="w-5 h-5 text-amber-500" />;
    return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
  };

  const getColor = (type: string) => {
    if (type === "Fraud") return "bg-rose-50 border-rose-100 text-rose-800";
    if (type === "Duplicate") return "bg-amber-50 border-amber-100 text-amber-800";
    return "bg-yellow-50 border-yellow-100 text-yellow-800";
  };

  if (loading) return <div className="animate-pulse h-[400px] bg-slate-100 rounded-2xl"></div>;

  const unresolvedAlerts = alerts.filter(a => !a.resolved);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-[500px]">
      <div className="p-5 border-b border-slate-100 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center">
            <BellRing className="w-4 h-4 text-rose-500" />
          </div>
          Action Center
        </h2>
        {unresolvedAlerts.length > 0 && (
          <span className="bg-rose-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {unresolvedAlerts.length}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/50">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
            <CheckCircle2 className="w-12 h-12 opacity-20 text-emerald-500" />
            <p className="font-medium text-center px-4">All clear! No pending actions or anomalies detected.</p>
          </div>
        ) : (
          alerts.map(alert => (
            <div key={alert.id} className={`p-4 rounded-xl border transition-all ${alert.resolved ? 'bg-white border-slate-200 opacity-60' : getColor(alert.alert_type)}`}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{getIcon(alert.alert_type)}</div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm">{alert.alert_type} Alert</h3>
                    <div className="flex items-center gap-2">
                      {alert.confidence_score && (
                        <span className="text-[10px] font-bold bg-white/50 px-1.5 py-0.5 rounded border border-black/5">
                          {alert.confidence_score}% CONFIDENCE
                        </span>
                      )}
                      <span className="text-xs font-medium opacity-60">{new Date(alert.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <p className="text-sm mt-1.5 opacity-90 leading-relaxed font-medium">{alert.message}</p>
                  {alert.explanation && (
                    <p className="text-[13px] mt-1 opacity-75 leading-relaxed">{alert.explanation}</p>
                  )}
                  
                  <div className="mt-4 flex items-center gap-3">
                    <Link href={`/document/${alert.document_id}`} className="text-sm font-bold flex items-center gap-1 hover:opacity-70 transition-opacity">
                      Review Document <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                    {!alert.resolved && (
                      <button 
                        onClick={() => resolveAlert(alert.id)}
                        className="text-sm font-medium opacity-60 hover:opacity-100 transition-opacity ml-auto"
                      >
                        Dismiss
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
