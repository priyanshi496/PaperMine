"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ArrowLeft, FileText, CheckCircle, RefreshCcw, Table2, Building, User, Receipt, Coins, ShieldCheck } from "lucide-react";
import axios from "axios";

interface ExtractedTable {
  id: number;
  page: number;
  rows: string[][];
}

interface DocumentData {
  id: number;
  filename: string;
  status: string;
  uploaded_at: string;
  ocr_text: string | null;
  summary: string | null;
  extraction_method: "direct" | "ocr" | null;
  tables: ExtractedTable[];
}

const PROCESSING_STATUSES = ["uploaded", "processing", "extracting_tables"];

export default function DocumentPage() {
  const { id } = useParams();
  const router = useRouter();
  const [doc, setDoc] = useState<DocumentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"ocr" | "tables">("ocr");

  const fetchDocument = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/api/v1/documents/${id}`);
      setDoc(res.data);
    } catch (err: any) {
      setError("Failed to load document data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchDocument();
    }
  }, [id]);

  const groupFields = (summaryStr: string | null) => {
    if (!summaryStr) return [];
    try {
      const data = JSON.parse(summaryStr);
      const groups = [
        {
          title: "Supplier Details",
          icon: <Building className="w-4 h-4 text-emerald-500" />,
          fields: {
            supplier_name: "Name",
            supplier_address: "Address",
            supplier_gstin: "GSTIN",
            supplier_contact: "Contact No",
            contact_no: "Contact No",
          }
        },
        {
          title: "Buyer Details",
          icon: <User className="w-4 h-4 text-blue-500" />,
          fields: {
            buyer_name: "Name",
            buyer_address: "Address",
            buyer_gstin: "GSTIN",
          }
        },
        {
          title: "Invoice & Supply",
          icon: <Receipt className="w-4 h-4 text-indigo-500" />,
          fields: {
            invoice_number: "Invoice No",
            invoice_date: "Invoice Date",
            date: "Date",
            place_of_supply: "Place of Supply",
            hsn_sac: "HSN/SAC Code",
            order_id: "Order ID",
            table_number: "Table",
            pay_mode: "Payment Mode",
            transaction_type: "Transaction Type",
          }
        },
        {
          title: "Tax & Financials",
          icon: <Coins className="w-4 h-4 text-amber-500" />,
          fields: {
            taxable_value: "Taxable Value (Pre-Tax)",
            subtotal: "Subtotal",
            tax_rate: "Tax Rate",
            tax_amount: "Tax Amount",
            cgst_rate: "CGST Rate",
            cgst_amount: "CGST Amount",
            sgst_rate: "SGST Rate",
            sgst_amount: "SGST Amount",
            igst_amount: "IGST Amount",
            total_amount: "Total Value",
            amount_in_words: "Amount in Words",
          }
        },
        {
          title: "Compliance & Delivery",
          icon: <ShieldCheck className="w-4 h-4 text-purple-500" />,
          fields: {
            signature_present: "Signature Present",
            reverse_charge: "Reverse Charge",
            shipping_address: "Shipping Address",
            transit_ref: "Transit/E-Way Ref",
          }
        }
      ];

      return groups.map(group => {
        const activeFields = Object.entries(group.fields)
          .map(([key, label]) => ({ key, label, val: data[key] }))
          .filter(f => {
            if (!f.val) return false;
            const value = (typeof f.val === "object" && f.val !== null && "value" in f.val) ? f.val.value : f.val;
            return value !== null && value !== undefined && value !== "";
          });
        return { ...group, activeFields };
      }).filter(g => g.activeFields.length > 0);
    } catch (e) {
      return [];
    }
  };

  const statusLabel: Record<string, string> = {
    uploaded: "Queued",
    processing: "Running OCR",
    extracting_tables: "Extracting Tables",
    processed: "Processed",
    error: "Error",
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
        <p className="text-red-500 font-medium">{error}</p>
        <button onClick={() => router.push("/")} className="mt-4 text-blue-500 hover:underline">
          Go back to dashboard
        </button>
      </div>
    );
  }

  const isProcessing = PROCESSING_STATUSES.includes(doc.status);
  const metadataGroups = groupFields(doc.summary);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans p-6">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500 font-medium">Status:</span>
            {doc.status === "processed" ? (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold uppercase tracking-wider">
                <CheckCircle className="w-3.5 h-3.5" /> Processed
              </span>
            ) : doc.status === "error" ? (
              <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold uppercase tracking-wider">
                Error
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold uppercase tracking-wider">
                <RefreshCcw className="w-3.5 h-3.5 animate-spin" />
                {statusLabel[doc.status] ?? doc.status}
              </span>
            )}
            {isProcessing && (
              <button
                onClick={fetchDocument}
                className="ml-2 p-1.5 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
                title="Refresh Status"
              >
                <RefreshCcw className="w-4 h-4 text-gray-700" />
              </button>
            )}
          </div>
        </header>

        {/* Document Info Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6 p-6 flex items-center gap-4">
          <div className="p-3 bg-blue-50 rounded-xl">
            <FileText className="w-6 h-6 text-blue-500" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-gray-900">{doc.filename}</h1>
            <div className="flex items-center gap-3 mt-1.5">
              <p className="text-sm text-gray-500">
                Uploaded: {new Date(doc.uploaded_at).toLocaleString()}
              </p>
              {doc.extraction_method && (
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                    doc.extraction_method === "direct"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-purple-100 text-purple-700"
                  }`}
                >
                  {doc.extraction_method === "direct" ? "⚡ Direct (No OCR)" : "🔍 OCR-Powered"}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Two-column layout: Left is Metadata Sidebar, Right is Content Tabs */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Column: Metadata Summary Card */}
          <div className="lg:col-span-1 bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-6">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-4">
              <CheckCircle className="w-5 h-5 text-blue-500" />
              <h2 className="text-base font-bold text-gray-800 tracking-tight">
                Document Summary
              </h2>
            </div>
            
            {metadataGroups.length > 0 ? (
              <div className="space-y-6 max-h-[600px] overflow-y-auto pr-1">
                {metadataGroups.map((group, idx) => (
                  <div key={idx} className="space-y-3">
                    <div className="flex items-center gap-1.5 border-b border-gray-50 pb-1.5">
                      {group.icon}
                      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                        {group.title}
                      </h3>
                    </div>
                    <div className="space-y-2.5 pl-5">
                      {group.activeFields.map(f => {
                        const hasMeta = typeof f.val === "object" && f.val !== null && "value" in f.val;
                        const dispVal = hasMeta ? f.val.value : f.val;
                        const source = hasMeta ? f.val.source : null;
                        const confidence = hasMeta ? f.val.confidence : null;

                        return (
                          <div key={f.key} className="space-y-0.5">
                            <span className="text-[10px] text-gray-400 font-medium block uppercase tracking-wider">
                              {f.label}
                            </span>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="text-sm text-gray-800 font-semibold break-words">
                                {typeof dispVal === "boolean" ? (dispVal ? "Yes" : "No") : String(dispVal)}
                              </span>
                              {source && (
                                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                                  source === "regex"
                                    ? "bg-emerald-50 text-emerald-600 border border-emerald-200"
                                    : "bg-blue-50 text-blue-600 border border-blue-200"
                                }`}>
                                  {source === "regex" ? "⚡ Regex" : "🤖 Gemini"}
                                  {confidence ? ` (${Math.round(confidence * 100)}%)` : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No summary fields extracted.</p>
            )}
          </div>

          {/* Right Column: OCR Text & Tables Content Tabs */}
          <div className="lg:col-span-2 space-y-4">
            {/* Tab Navigation */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
              <button
                onClick={() => setActiveTab("ocr")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === "ocr"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <FileText className="w-4 h-4" />
                OCR Text
              </button>
              <button
                onClick={() => setActiveTab("tables")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === "tables"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <Table2 className="w-4 h-4" />
                Tables
                {doc.tables.length > 0 && (
                  <span className="ml-1 bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {doc.tables.length}
                  </span>
                )}
              </button>
            </div>

            {/* Content Panel */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 min-h-[600px] flex flex-col overflow-hidden">

              {/* OCR Text Tab */}
              {activeTab === "ocr" && (
                <div className="flex-1 p-6 overflow-y-auto whitespace-pre-wrap font-mono text-sm text-gray-700 leading-relaxed">
                  {doc.ocr_text ? (
                    doc.ocr_text
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-3">
                      <FileText className="w-12 h-12 opacity-30" />
                      <p className="font-medium">
                        {isProcessing ? "Extracting text… click refresh to update." : "No text extracted yet."}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Tables Tab */}
              {activeTab === "tables" && (
                <div className="flex-1 p-6 overflow-y-auto">
                  {doc.tables.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-3">
                      <Table2 className="w-12 h-12 opacity-30" />
                      <p className="font-medium">
                        {isProcessing
                          ? "Table extraction in progress… click refresh to update."
                          : "No tables were found in this document."}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-10">
                      {doc.tables.map((table) => (
                        <div key={table.id}>
                          <div className="flex items-center gap-2 mb-3">
                            <Table2 className="w-4 h-4 text-blue-500" />
                            <span className="text-sm font-semibold text-gray-700">
                              Table on Page {table.page}
                            </span>
                          </div>
                          <div className="overflow-x-auto rounded-xl border border-gray-200">
                            <table className="w-full text-sm text-left">
                              <thead>
                                <tr className="bg-gray-50 border-b border-gray-200">
                                  {table.rows[0]?.map((header, i) => (
                                    <th
                                      key={i}
                                      className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide"
                                    >
                                      {header || <span className="text-gray-300 italic">—</span>}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {table.rows.slice(1).map((row, rowIdx) => (
                                  <tr
                                    key={rowIdx}
                                    className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors"
                                  >
                                    {row.map((cell, cellIdx) => (
                                      <td key={cellIdx} className="px-4 py-3 text-gray-700">
                                        {cell || <span className="text-gray-300">—</span>}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
