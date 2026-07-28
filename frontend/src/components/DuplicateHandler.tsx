"use client";

import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { AlertTriangle, FileText, CheckCircle, XCircle, ArrowRight, Loader2, AlertCircle } from "lucide-react";

export default function DuplicateHandler({ documentId, status }: { documentId: string, status: string }) {
  const router = useRouter();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [error, setError] = useState("");

  const isFraud = status === "duplicate_fraud";
  const isFileDuplicate = status === "duplicate_file";

  const handleAction = async (action: string) => {
    setLoadingAction(action);
    setError("");
    try {
      if (action === "cancel") {
        await axios.post(`http://localhost:8000/api/v1/documents/${documentId}/cancel`);
        router.push("/");
      } else if (action === "replace") {
        const res = await axios.post(`http://localhost:8000/api/v1/documents/${documentId}/replace-existing`);
        // The endpoint deleted the duplicate doc and updated the existing invoice. 
        // Redirect back to the dashboard or to the existing invoice.
        router.push("/");
      } else if (action === "force") {
        const res = await axios.post(`http://localhost:8000/api/v1/documents/${documentId}/force-create-new`);
        // Refresh the page or reload data for the new invoice.
        window.location.reload();
      } else if (action === "scan") {
        const res = await axios.post(`http://localhost:8000/api/v1/documents/${documentId}/scan`);
        // Refresh the page to trigger polling
        window.location.reload();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "An error occurred.");
      setLoadingAction(null);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      <div className={`rounded-xl border ${isFraud ? 'border-rose-200 bg-white shadow-rose-100' : 'border-amber-200 bg-white shadow-amber-100'} shadow-xl overflow-hidden`}>
        
        {/* Header */}
        <div className={`p-6 border-b flex items-start gap-4 ${isFraud ? 'bg-rose-50 border-rose-100' : 'bg-amber-50 border-amber-100'}`}>
          <div className={`p-3 rounded-full shrink-0 ${isFraud ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'}`}>
            {isFraud ? <AlertCircle className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
          </div>
          <div>
            <h2 className={`text-xl font-bold ${isFraud ? 'text-rose-900' : 'text-amber-900'}`}>
              {isFileDuplicate 
                ? "⚠ File Duplication Found"
                : (isFraud ? "🚨 High Risk Alert" : "⚠ Duplicate Invoice Detected")}
            </h2>
            <p className={`mt-2 font-medium ${isFraud ? 'text-rose-700' : 'text-amber-700'}`}>
              {isFileDuplicate 
                ? "This exact file has already been uploaded previously. The AI has intercepted it to save processing costs."
                : (isFraud 
                  ? "An invoice with this number already exists, but the financial values differ. This is a possible edited invoice." 
                  : "An invoice with this exact number from the same vendor already exists in the system.")}
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          
          {error && (
            <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm font-medium border border-red-100">
              {error}
            </div>
          )}

          <div className="text-sm font-medium text-slate-600">
            Please choose how you would like to proceed with this upload.
          </div>

          <div className="space-y-3">
            {isFileDuplicate ? (
              <button 
                onClick={() => handleAction("scan")}
                disabled={loadingAction !== null}
                className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-left disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800">Continue Scanning Anyway</h3>
                    <p className="text-xs font-medium text-slate-500 mt-0.5">Force the AI to process this file and extract its contents.</p>
                  </div>
                </div>
                {loadingAction === "scan" ? <Loader2 className="w-5 h-5 animate-spin text-indigo-500" /> : <ArrowRight className="w-5 h-5 text-slate-400" />}
              </button>
            ) : (
              <>
                <button 
                  onClick={() => handleAction("replace")}
                  disabled={loadingAction !== null}
                  className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-left disabled:opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-800">Replace Existing OCR</h3>
                      <p className="text-xs font-medium text-slate-500 mt-0.5">Update the existing invoice with this new extraction (fixes bad OCR).</p>
                    </div>
                  </div>
                  {loadingAction === "replace" ? <Loader2 className="w-5 h-5 animate-spin text-indigo-500" /> : <ArrowRight className="w-5 h-5 text-slate-400" />}
                </button>

                <button 
                  onClick={() => handleAction("force")}
                  disabled={loadingAction !== null}
                  className={`w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 hover:bg-slate-50 transition-all text-left disabled:opacity-50 ${isFraud ? 'hover:border-rose-300 hover:bg-rose-50/50' : 'hover:border-amber-300 hover:bg-amber-50/50'}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 text-slate-600 rounded-lg">
                      <CheckCircle className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-800">Save as New Invoice Anyway</h3>
                      <p className="text-xs font-medium text-slate-500 mt-0.5">Force the system to create a second invoice with the same number.</p>
                    </div>
                  </div>
                  {loadingAction === "force" ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" /> : <ArrowRight className="w-5 h-5 text-slate-400" />}
                </button>
              </>
            )}

            <button 
              onClick={() => handleAction("cancel")}
              disabled={loadingAction !== null}
              className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all text-left disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-100 text-slate-600 rounded-lg">
                  <XCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">Cancel Upload</h3>
                  <p className="text-xs font-medium text-slate-500 mt-0.5">Safely discard this file and return to the dashboard.</p>
                </div>
              </div>
              {loadingAction === "cancel" ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" /> : <ArrowRight className="w-5 h-5 text-slate-400" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
