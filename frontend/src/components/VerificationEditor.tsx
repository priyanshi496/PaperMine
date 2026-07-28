"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { CheckCircle, AlertCircle, Save, Building2, Receipt, Coins, Loader2, Lock, AlertTriangle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface InsightAlert {
  id: number;
  alert_type: string;
  severity: string;
  message: string;
  explanation: string;
  confidence_score: number;
}

interface InvoiceData {
  id: number;
  vendor_name: string;
  vendor_gstin: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: string;
  tax_amount: string;
  verification_status: string;
  vendor_bank_account: string;
  vendor_ifsc: string;
  vendor_address: string;
  vendor_is_verified: boolean;
  alerts: InsightAlert[];
}

export default function VerificationEditor({ documentId, isProcessing }: { documentId: string, isProcessing?: boolean }) {
  const { authState } = useAuth();
  const [invoice, setInvoice] = useState<InvoiceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // Editable form state
  const [formData, setFormData] = useState({
    vendor_name: "",
    vendor_gstin: "",
    invoice_number: "",
    invoice_date: "",
    total_amount: "",
    tax_amount: "",
    vendor_bank_account: "",
    vendor_ifsc: "",
    vendor_address: "",
  });

  useEffect(() => {
    if (isProcessing) return; // Don't fetch while the AI pipeline is running
    
    const fetchInvoice = async () => {
      try {
        const res = await axios.get(`http://localhost:8000/api/v1/invoices/document/${documentId}`);
        if (res.data) {
          setInvoice(res.data);
          setFormData({
            vendor_name: res.data.vendor_name || "",
            vendor_gstin: res.data.vendor_gstin || "",
            invoice_number: res.data.invoice_number || "",
            invoice_date: res.data.invoice_date || "",
            total_amount: res.data.total_amount || "",
            tax_amount: res.data.tax_amount || "",
            vendor_bank_account: res.data.vendor_bank_account || "",
            vendor_ifsc: res.data.vendor_ifsc || "",
            vendor_address: res.data.vendor_address || "",
          });
        }
      } catch (err) {
        setError("Invoice data not found or still processing.");
      } finally {
        setLoading(false);
      }
    };
    fetchInvoice();
  }, [documentId, isProcessing]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setSuccess(false);
  };

  const handleVerify = async () => {
    if (!invoice) return;
    setSaving(true);
    try {
      await axios.put(`http://localhost:8000/api/v1/invoices/${invoice.id}/verify`, formData);
      setInvoice({ ...invoice, ...formData, verification_status: "Verified", vendor_is_verified: true });
      setSuccess(true);
    } catch (err) {
      console.error(err);
      setError("Failed to verify invoice.");
    } finally {
      setSaving(false);
    }
  };

  if (loading || isProcessing) return (
    <div className="flex flex-col items-center justify-center text-slate-400 py-12">
      <Loader2 className="w-8 h-8 opacity-20 mb-3 animate-spin text-indigo-500" />
      <p className="font-medium">{isProcessing ? "AI Engine is analyzing the invoice..." : "Loading verification data..."}</p>
    </div>
  );
  
  if (!invoice) return (
    <div className="flex flex-col items-center justify-center text-slate-400 py-12">
      <AlertCircle className="w-8 h-8 opacity-20 mb-3 text-rose-500" />
      <p className="font-medium">{error || "No invoice data available."}</p>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-8 pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Data Verification</h2>
          <p className="text-sm text-slate-500 mt-1">Review AI extracted fields and correct anomalies.</p>
        </div>
        {invoice.verification_status === "Verified" ? (
          <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-bold uppercase tracking-wider border border-emerald-100">
            <CheckCircle className="w-4 h-4" /> Verified
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs font-bold uppercase tracking-wider border border-amber-100">
            <AlertCircle className="w-4 h-4" /> Unverified
          </span>
        )}
      </div>

      <div className="space-y-6">
        
        {/* Business Profile Section */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between bg-slate-50 px-5 py-3 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-indigo-500" />
              <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Business Profile (Verified)</h3>
            </div>
            {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400" />}
          </div>
          
          <div className="p-5 space-y-4">
            {!invoice.vendor_is_verified && (
              <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
                <p className="text-sm text-indigo-800 font-medium leading-relaxed">
                  This information is saved as your business identity and will be used to verify future invoices. Please verify them carefully.
                </p>
              </div>
            )}
            
            {invoice.vendor_is_verified && (
              <p className="text-xs text-slate-500 font-medium">
                These details are verified from your business profile. Contact an administrator if they need to be updated.
              </p>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Vendor Name</label>
                <div className="relative">
                  <input type="text" name="vendor_name" value={formData.vendor_name} onChange={handleChange} disabled={invoice.vendor_is_verified}
                    className={`w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none text-sm font-medium text-slate-900 ${invoice.vendor_is_verified ? 'opacity-70 cursor-not-allowed pr-8' : 'hover:bg-white focus:bg-white focus:border-indigo-500 transition-all'}`}
                  />
                  {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />}
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Vendor GSTIN</label>
                <div className="relative">
                  <input type="text" name="vendor_gstin" value={formData.vendor_gstin} onChange={handleChange} disabled={invoice.vendor_is_verified}
                    className={`w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none text-sm font-medium text-slate-900 font-mono ${invoice.vendor_is_verified ? 'opacity-70 cursor-not-allowed pr-8' : 'hover:bg-white focus:bg-white focus:border-indigo-500 transition-all'}`}
                  />
                  {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />}
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Bank Account</label>
                <div className="relative">
                  <input type="text" name="vendor_bank_account" value={formData.vendor_bank_account} onChange={handleChange} disabled={invoice.vendor_is_verified}
                    className={`w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none text-sm font-medium text-slate-900 font-mono ${invoice.vendor_is_verified ? 'opacity-70 cursor-not-allowed pr-8' : 'hover:bg-white focus:bg-white focus:border-indigo-500 transition-all'}`}
                  />
                  {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />}
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">IFSC Code</label>
                <div className="relative">
                  <input type="text" name="vendor_ifsc" value={formData.vendor_ifsc} onChange={handleChange} disabled={invoice.vendor_is_verified}
                    className={`w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none text-sm font-medium text-slate-900 font-mono ${invoice.vendor_is_verified ? 'opacity-70 cursor-not-allowed pr-8' : 'hover:bg-white focus:bg-white focus:border-indigo-500 transition-all'}`}
                  />
                  {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />}
                </div>
              </div>
            </div>
            
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 uppercase">Address</label>
              <div className="relative">
                <input type="text" name="vendor_address" value={formData.vendor_address} onChange={handleChange} disabled={invoice.vendor_is_verified}
                  className={`w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg outline-none text-sm font-medium text-slate-900 ${invoice.vendor_is_verified ? 'opacity-70 cursor-not-allowed pr-8' : 'hover:bg-white focus:bg-white focus:border-indigo-500 transition-all'}`}
                />
                {invoice.vendor_is_verified && <Lock className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />}
              </div>
            </div>
          </div>
        </div>

        {/* Current Invoice Section */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 bg-slate-50 px-5 py-3 border-b border-slate-200">
            <Receipt className="w-4 h-4 text-emerald-500" />
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Current Invoice ✏️</h3>
          </div>
          
          <div className="p-5 space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Invoice Number</label>
                <input type="text" name="invoice_number" value={formData.invoice_number} onChange={handleChange}
                  className="w-full px-3 py-2 bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-lg outline-none transition-all text-sm font-medium text-slate-900 font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Invoice Date</label>
                <input type="text" name="invoice_date" value={formData.invoice_date} onChange={handleChange}
                  className="w-full px-3 py-2 bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-lg outline-none transition-all text-sm font-medium text-slate-900"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-2 border-b border-slate-100 pb-2 pt-2">
              <Coins className="w-4 h-4 text-amber-500" />
              <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wide">Financials</h4>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Total Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">₹</span>
                  <input type="text" name="total_amount" value={formData.total_amount} onChange={handleChange}
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-lg outline-none transition-all text-sm font-bold text-slate-900 font-mono"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase">Tax Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">₹</span>
                  <input type="text" name="tax_amount" value={formData.tax_amount} onChange={handleChange}
                    className="w-full pl-8 pr-3 py-2 bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 focus:border-indigo-500 rounded-lg outline-none transition-all text-sm font-bold text-slate-900 font-mono"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* AI Warnings Section */}
        {invoice.alerts && invoice.alerts.length > 0 && (
          <div className="bg-white rounded-xl border border-rose-200 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 bg-rose-50/50 px-5 py-3 border-b border-rose-100">
              <AlertTriangle className="w-4 h-4 text-rose-500" />
              <h3 className="text-sm font-bold text-rose-800 uppercase tracking-wide">AI Warnings</h3>
            </div>
            
            <div className="p-5 space-y-3">
              {invoice.alerts.map((alert) => (
                <div key={alert.id} className={`flex items-start gap-3 p-4 border rounded-xl ${
                  alert.severity === 'high' ? 'bg-rose-50 border-rose-200' : 
                  alert.severity === 'medium' ? 'bg-amber-50 border-amber-200' : 
                  'bg-yellow-50 border-yellow-200'
                }`}>
                  {alert.severity === 'high' ? (
                    <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                  ) : alert.severity === 'medium' ? (
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h4 className={`text-sm font-bold ${
                      alert.severity === 'high' ? 'text-rose-900' : 
                      alert.severity === 'medium' ? 'text-amber-900' : 
                      'text-yellow-800'
                    }`}>
                      {alert.message}
                    </h4>
                    <p className={`text-xs mt-1 font-medium ${
                      alert.severity === 'high' ? 'text-rose-700' : 
                      alert.severity === 'medium' ? 'text-amber-700' : 
                      'text-yellow-700'
                    }`}>
                      {alert.explanation}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      <div className="flex items-center justify-between pt-6 border-t border-slate-100">
        {success ? (
          <span className="text-emerald-600 text-sm font-bold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-100">
            <CheckCircle className="w-4 h-4"/> Saved successfully!
          </span>
        ) : (
          <div></div>
        )}
        <button
          onClick={handleVerify}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-70 disabled:shadow-none"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {invoice.verification_status === "Verified" ? "Update Details" : "Verify & Save"}
        </button>
      </div>
    </div>
  );
}
