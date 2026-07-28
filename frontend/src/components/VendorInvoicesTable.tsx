"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { FileText, CheckCircle, AlertCircle, ArrowRight, Search, Download } from "lucide-react";
import Link from "next/link";

interface Invoice {
  id: number;
  document_id: number;
  invoice_number: string;
  total_amount: string;
  verification_status: string;
}

export default function VendorInvoicesTable() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        const res = await axios.get("http://localhost:8000/api/v1/invoices");
        setInvoices(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchInvoices();
  }, []);

  if (loading) return <div className="animate-pulse h-[400px] w-full bg-slate-100 rounded-2xl"></div>;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-[500px]">
      
      {/* Header */}
      <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
            <FileText className="w-4 h-4 text-indigo-600" />
          </div>
          Invoice History
        </h2>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search..." 
              className="pl-9 pr-4 py-1.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors">
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="flex-1 overflow-y-auto">
        {invoices.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
            <FileText className="w-12 h-12 opacity-20" />
            <p className="font-medium">No invoices found. Upload a document to get started.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 backdrop-blur-md sticky top-0 z-10 text-slate-500 uppercase text-xs tracking-wider font-semibold border-b border-slate-100">
              <tr>
                <th className="px-6 py-4">Invoice No</th>
                <th className="px-6 py-4">Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 bg-white">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-6 py-4">
                    <span className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {inv.invoice_number || "Unknown"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600 font-medium">
                    {inv.total_amount ? `₹${Number(inv.total_amount).toLocaleString()}` : "—"}
                  </td>
                  <td className="px-6 py-4">
                    {inv.verification_status === "Verified" ? (
                      <span className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs bg-emerald-50 px-2.5 py-1 rounded-full w-fit border border-emerald-100">
                        <CheckCircle className="w-3.5 h-3.5" /> VERIFIED
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-amber-700 font-bold text-xs bg-amber-50 px-2.5 py-1 rounded-full w-fit border border-amber-100">
                        <AlertCircle className="w-3.5 h-3.5" /> PENDING
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/document/${inv.document_id}`}
                      className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-semibold bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Review <ArrowRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
