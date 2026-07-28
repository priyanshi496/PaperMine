"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ArrowLeft, FileText, CheckCircle, RefreshCcw, Table2, ShieldCheck, Download, Code, FileCode2 } from "lucide-react";
import axios from "axios";

import VerificationEditor from "@/components/VerificationEditor";
import EditableJsonTable from "@/components/EditableJsonTable";
import DuplicateHandler from "@/components/DuplicateHandler";

interface DocumentData {
  id: number;
  filename: string;
  status: string;
  uploaded_at: string;
  ocr_text: string | null;
  summary: string | null;
  extraction_method: "direct" | "ocr" | null;
  tables: any[];
}

const PROCESSING_STATUSES = ["uploaded", "processing", "correcting_low_confidence", "extracting_tables"];

export default function DocumentPage() {
  const { id } = useParams();
  const router = useRouter();
  const [doc, setDoc] = useState<DocumentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"verification" | "ocr" | "json">("verification");
  const [fileBlobUrl, setFileBlobUrl] = useState<string | null>(null);

  const fetchDocument = async (isPolling = false) => {
    if (!isPolling) setLoading(true);
    try {
      const res = await axios.get(`http://localhost:8000/api/v1/documents/${id}`);
      setDoc(res.data);
      
      // Fetch the file securely using the Auth headers
      const fileRes = await axios.get(`http://localhost:8000/api/v1/documents/${id}/file`, {
        responseType: 'blob'
      });
      const url = URL.createObjectURL(fileRes.data);
      setFileBlobUrl(url);

    } catch (err: any) {
      if (!isPolling) setError("Failed to load document data.");
    } finally {
      if (!isPolling) setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchDocument();
    
    return () => {
        if (fileBlobUrl) URL.revokeObjectURL(fileBlobUrl);
    };
  }, [id]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    
    if (doc && PROCESSING_STATUSES.includes(doc.status)) {
        intervalId = setInterval(() => {
            fetchDocument(true);
        }, 3000);
    }
    
    return () => {
        if (intervalId) clearInterval(intervalId);
    };
  }, [id, doc?.status]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-900">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-50">
        <p className="text-rose-500 font-medium">{error}</p>
        <button onClick={() => router.push("/")} className="mt-4 text-indigo-500 hover:underline">
          Go back to dashboard
        </button>
      </div>
    );
  }

  const isProcessing = PROCESSING_STATUSES.includes(doc.status);

  return (
    <div className="h-screen w-full bg-slate-50 flex flex-col overflow-hidden">
      
      {/* Top Action Bar */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          
          <div className="h-4 w-px bg-slate-300"></div>
          
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-500" />
            <span className="text-sm font-bold text-slate-700">{doc.filename}</span>
          </div>
          
          {doc.status === "processed" ? (
            <span className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border border-emerald-100">
              <CheckCircle className="w-3 h-3" /> Processed
            </span>
          ) : (
            <span className="flex items-center gap-1 bg-amber-50 text-amber-700 px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border border-amber-100">
              <RefreshCcw className="w-3 h-3 animate-spin" /> {doc.status}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {isProcessing && (
            <button onClick={fetchDocument} className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-md transition-colors">
              <RefreshCcw className="w-3.5 h-3.5" /> Refresh Status
            </button>
          )}
          <button className="flex items-center gap-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 rounded-md transition-colors shadow-sm shadow-indigo-600/20">
            <Download className="w-3.5 h-3.5" /> Download JSON
          </button>
        </div>
      </header>

      {/* Split Screen Workspace */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left: Document Viewer Placeholder */}
        <div className="w-1/2 bg-slate-200/50 border-r border-slate-200 flex flex-col relative">
          <div className="absolute top-4 left-4 bg-white/90 backdrop-blur text-xs font-bold text-slate-500 px-3 py-1.5 rounded-lg shadow-sm z-10 border border-slate-200">
            Document Viewer (PDF / Image)
          </div>
          <div className="flex-1 w-full h-full p-4 pt-16">
             <div className="w-full h-full bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                {fileBlobUrl ? (
                  doc.filename.toLowerCase().endsWith('.pdf') ? (
                    <embed 
                      src={fileBlobUrl} 
                      className="w-full h-full"
                      type="application/pdf"
                    />
                  ) : (
                    <img 
                      src={fileBlobUrl} 
                      className="w-full h-full object-contain bg-slate-100"
                      alt={doc.filename}
                    />
                  )
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                    <RefreshCcw className="w-12 h-12 mb-4 animate-spin opacity-20" />
                    <p className="font-medium text-sm">Loading Document...</p>
                  </div>
                )}
             </div>
          </div>
        </div>

        {/* Right: Interactive Editor */}
        <div className="w-1/2 bg-white flex flex-col">
          
          {/* Tab Navigation */}
          <div className="h-12 border-b border-slate-100 flex items-center px-2 bg-slate-50/50">
            <button
              onClick={() => setActiveTab("verification")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-bold transition-colors border-b-2 rounded-t-lg ${
                activeTab === "verification"
                  ? "border-indigo-500 text-indigo-600 bg-indigo-50/50"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100/50"
              }`}
            >
              <ShieldCheck className="w-4 h-4" /> Human Verification
            </button>
            <button
              onClick={() => setActiveTab("ocr")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-bold transition-colors border-b-2 rounded-t-lg ${
                activeTab === "ocr"
                  ? "border-indigo-500 text-indigo-600 bg-indigo-50/50"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100/50"
              }`}
            >
              <FileCode2 className="w-4 h-4" /> Raw OCR Text
            </button>
            <button
              onClick={() => setActiveTab("json")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-bold transition-colors border-b-2 rounded-t-lg ${
                activeTab === "json"
                  ? "border-indigo-500 text-indigo-600 bg-indigo-50/50"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100/50"
              }`}
            >
              <Code className="w-4 h-4" /> Extracted Data
            </button>
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto bg-slate-50/30">
            
            {activeTab === "verification" && (
              <div className="p-6">
                {doc.status.startsWith("duplicate") ? (
                  <DuplicateHandler documentId={id as string} status={doc.status} />
                ) : (
                  <VerificationEditor documentId={id as string} isProcessing={isProcessing} />
                )}
              </div>
            )}

            {activeTab === "ocr" && (
              <div className="p-6 font-mono text-[13px] text-slate-700 leading-relaxed whitespace-pre-wrap">
                {doc.ocr_text ? (
                  doc.ocr_text
                ) : (
                  <div className="flex flex-col items-center justify-center text-slate-400 py-12">
                    <RefreshCcw className="w-8 h-8 opacity-20 mb-3 animate-spin" />
                    <p className="font-medium">OCR Engine is currently processing...</p>
                  </div>
                )}
              </div>
            )}
            
            {activeTab === "json" && (
              <EditableJsonTable 
                documentId={id as string} 
                initialJsonStr={doc.summary}
                onSaveSuccess={() => {
                  fetchDocument();
                }}
              />
            )}
            
          </div>
        </div>
      </div>
    </div>
  );
}
