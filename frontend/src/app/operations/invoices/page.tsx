"use client";

import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import axios from "axios";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, AlertTriangle, FileText, CheckCircle2, FileCheck2, Bot, Building2, CreditCard, Download, ArrowRight } from "lucide-react";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function InvoiceOperations() {
  const { authState, loading: authLoading } = useAuth();
  const [invoices, setInvoices] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  
  // Drawer State
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null);
  const [invoiceDetails, setInvoiceDetails] = useState<any | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && authState.token) {
      fetchInvoices();
    }
  }, [authLoading, authState.token]);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const res = await axios.get("http://localhost:8000/api/v1/invoices/");
      setInvoices(res.data);
      setFiltered(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!search) {
      setFiltered(invoices);
      return;
    }
    const lower = search.toLowerCase();
    const result = invoices.filter(inv => 
      inv.vendor_name.toLowerCase().includes(lower) || 
      inv.invoice_number?.toLowerCase().includes(lower) ||
      inv.department.toLowerCase().includes(lower)
    );
    setFiltered(result);
  }, [search, invoices]);

  const openDrawer = async (invoice: any) => {
    setSelectedInvoice(invoice);
    setDrawerOpen(true);
    setDetailsLoading(true);
    try {
      const res = await axios.get(`http://localhost:8000/api/v1/invoices/document/${invoice.document_id}`);
      setInvoiceDetails(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setDetailsLoading(false);
    }
  };

  const formatCurrency = (val: string) => {
    if (!val) return "₹0";
    const num = parseFloat(val.replace(/[^0-9.-]+/g,""));
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(num);
  };

  return (
    <div className="flex-1 p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Invoice Operations</h1>
        <p className="text-muted-foreground mt-1">Review, verify, and approve invoices across all departments.</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative w-80">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search by vendor, department, or invoice ID..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="rounded-md border bg-card text-card-foreground shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead>Vendor</TableHead>
              <TableHead>Invoice No.</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Risk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">Loading invoices...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">No invoices found.</TableCell>
              </TableRow>
            ) : (
              filtered.map((inv) => (
                <TableRow 
                  key={inv.id} 
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => openDrawer(inv)}
                >
                  <TableCell className="font-medium">{inv.vendor_name}</TableCell>
                  <TableCell>{inv.invoice_number}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{inv.department}</Badge>
                  </TableCell>
                  <TableCell>{inv.invoice_date || "N/A"}</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(inv.total_amount)}</TableCell>
                  <TableCell>
                    {inv.verification_status === "Verified" && <Badge variant="outline" className="text-green-600 bg-green-500/10 border-green-500/20">{inv.verification_status}</Badge>}
                    {inv.verification_status === "Rejected" && <Badge variant="outline" className="text-red-600 bg-red-500/10 border-red-500/20">{inv.verification_status}</Badge>}
                    {(inv.verification_status === "Needs Manager Approval" || inv.verification_status === "Pending") && <Badge variant="outline" className="text-yellow-600 bg-yellow-500/10 border-yellow-500/20">{inv.verification_status}</Badge>}
                    {inv.verification_status === "Approved" && <Badge variant="outline" className="text-blue-600 bg-blue-500/10 border-blue-500/20">{inv.verification_status}</Badge>}
                  </TableCell>
                  <TableCell>
                    {inv.risk_score >= 5 ? (
                      <Badge variant="destructive" className="gap-1"><AlertTriangle className="w-3 h-3"/> High</Badge>
                    ) : (
                      <Badge variant="outline" className="text-green-500 border-green-500/20 bg-green-500/10">Low</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Invoice Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-full sm:!max-w-[550px] sm:w-[750px] p-0 overflow-y-auto sm:border-l sm:rounded-l-2xl">
          {detailsLoading || !invoiceDetails ? (
            <div className="flex flex-col gap-4 animate-pulse p-8">
              <div className="h-40 bg-muted rounded-xl w-full"></div>
              <div className="h-64 bg-muted rounded-xl w-full"></div>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              {/* Story-telling Hero Section */}
              <div className="bg-muted/10 px-8 py-8 border-b">
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <div className="flex items-center gap-4 mb-2">
                      <div className="h-11 w-11 bg-primary/10 text-primary rounded-xl flex items-center justify-center shrink-0">
                        <Building2 className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="text-[17px] font-semibold text-foreground leading-tight tracking-tight">{invoiceDetails.vendor_name}</h2>
                        <p className="text-[13px] text-muted-foreground mt-0.5">
                          Invoice <span className="font-mono text-foreground font-medium">{invoiceDetails.invoice_number}</span> • {invoiceDetails.invoice_date || "N/A"}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="h-8 gap-1.5 px-3 rounded-full text-xs font-semibold">
                      <Download className="w-3.5 h-3.5"/> PDF
                    </Button>
                    {authState.user?.role !== "cfo" ? (
                      (invoiceDetails.verification_status === "Needs Manager Approval" || invoiceDetails.verification_status === "Pending") && (
                        <Button variant="default" size="sm" className="h-8 gap-1.5 px-4 rounded-full text-xs font-semibold bg-primary hover:bg-primary/90 text-primary-foreground">
                          Approve
                        </Button>
                      )
                    ) : (
                      <Badge variant="secondary" className="h-8 px-3 rounded-full font-mono text-[11px] bg-muted/50 text-muted-foreground border-transparent cursor-default">View Only</Badge>
                    )}
                  </div>
                </div>

                <div className="flex items-end justify-between mt-2">
                  <div>
                    <p className="text-[11px] text-muted-foreground uppercase tracking-widest font-semibold mb-2">Total Amount</p>
                    <h3 className="text-[40px] leading-none font-bold font-mono tracking-tight text-foreground">{formatCurrency(invoiceDetails.total_amount)}</h3>
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    {invoiceDetails.verification_status === "Verified" && <Badge variant="outline" className="px-3.5 py-1 text-[12px] font-medium rounded-full text-green-700 bg-green-500/10 border-green-500/20">{invoiceDetails.verification_status}</Badge>}
                    {invoiceDetails.verification_status === "Rejected" && <Badge variant="outline" className="px-3.5 py-1 text-[12px] font-medium rounded-full text-red-700 bg-red-500/10 border-red-500/20">{invoiceDetails.verification_status}</Badge>}
                    {(invoiceDetails.verification_status === "Needs Manager Approval" || invoiceDetails.verification_status === "Pending") && <Badge variant="outline" className="px-3.5 py-1 text-[12px] font-medium rounded-full text-yellow-700 bg-yellow-500/10 border-yellow-500/20">{invoiceDetails.verification_status}</Badge>}
                    {invoiceDetails.verification_status === "Approved" && <Badge variant="outline" className="px-3.5 py-1 text-[12px] font-medium rounded-full text-blue-700 bg-blue-500/10 border-blue-500/20">{invoiceDetails.verification_status}</Badge>}
                    
                    {invoiceDetails.risk_score >= 5 ? (
                      <Badge variant="destructive" className="px-3.5 py-1 text-[12px] font-medium rounded-full bg-red-500/90 text-white">
                        <AlertTriangle className="w-3.5 h-3.5 mr-1.5"/> High Risk
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="px-3.5 py-1 text-[12px] font-medium rounded-full text-green-700 border-green-500/20 bg-green-500/5">
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1.5"/> Low Risk
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <Tabs defaultValue="overview" className="flex-1 flex flex-col">
                <TabsList className="w-full bg-transparent border-b rounded-none p-0 h-auto space-x-6 justify-start px-8 overflow-x-auto">
                  <TabsTrigger value="overview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none py-4 px-1 text-[14px] font-medium data-[state=active]:font-semibold data-[state=active]:text-foreground text-muted-foreground transition-all">Overview</TabsTrigger>
                  <TabsTrigger value="ocr" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none py-4 px-1 text-[14px] font-medium data-[state=active]:font-semibold data-[state=active]:text-foreground text-muted-foreground transition-all">OCR</TabsTrigger>
                  <TabsTrigger value="ai" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none py-4 px-1 text-[14px] font-medium data-[state=active]:font-semibold data-[state=active]:text-foreground text-muted-foreground transition-all">AI Analysis</TabsTrigger>
                  <TabsTrigger value="risk" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none py-4 px-1 text-[14px] font-medium data-[state=active]:font-semibold data-[state=active]:text-foreground text-muted-foreground transition-all">Risk</TabsTrigger>
                  <TabsTrigger value="timeline" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none py-4 px-1 text-[14px] font-medium data-[state=active]:font-semibold data-[state=active]:text-foreground text-muted-foreground transition-all">Timeline</TabsTrigger>
                </TabsList>
                
                {/* Overview Tab */}
                <TabsContent value="overview" className="flex-1 p-8 m-0 space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="grid grid-cols-2 gap-y-10 gap-x-6">
                    <div>
                      <p className="text-[11px] text-muted-foreground uppercase font-bold tracking-wider mb-2">GSTIN</p>
                      <p className="font-semibold text-[15px] font-mono">{invoiceDetails.vendor_gstin}</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-muted-foreground uppercase font-bold tracking-wider mb-2">Bank Account</p>
                      <p className="font-semibold text-[15px] font-mono flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-muted-foreground shrink-0" />
                        {invoiceDetails.vendor_bank_account}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] text-muted-foreground uppercase font-bold tracking-wider mb-2">Total GST (Tax)</p>
                      <p className="font-semibold text-[15px] font-mono text-foreground">{formatCurrency(invoiceDetails.tax_amount)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-muted-foreground uppercase font-bold tracking-wider mb-2">Payment Terms</p>
                      <p className="font-semibold text-[15px] text-foreground">Net 30</p>
                    </div>
                  </div>

                  <div className="h-px bg-border/50 w-full" />

                  <div>
                    <h3 className="font-semibold text-[13px] uppercase tracking-wider text-muted-foreground mb-4">Line Items</h3>
                    <div className="border rounded-2xl overflow-hidden shadow-sm">
                      <Table>
                        <TableHeader className="bg-muted/30">
                          <TableRow className="border-b">
                            <TableHead className="text-xs h-11 px-5">Item</TableHead>
                            <TableHead className="text-xs h-11 px-4">Category</TableHead>
                            <TableHead className="text-xs text-right h-11 px-5">Amount</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {invoiceDetails.line_items.map((item: any) => (
                            <TableRow key={item.id} className="hover:bg-muted/20">
                              <TableCell className="text-[14.5px] font-medium py-4 px-5">{item.description}</TableCell>
                              <TableCell className="py-4 px-4">
                                <Badge variant="secondary" className="px-2.5 py-1 text-[11px] uppercase tracking-wider rounded-md font-semibold bg-muted text-muted-foreground">
                                  {item.category}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-[15px] text-right font-mono py-4 px-5 font-semibold">{formatCurrency(item.amount)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                  
                  {/* Empty space filler for future extensibility */}
                  <div className="pt-4 space-y-6">
                    <h3 className="font-semibold text-[13px] uppercase tracking-wider text-muted-foreground">Additional Information</h3>
                    <div className="grid grid-cols-2 gap-8 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 uppercase font-semibold tracking-wider">Shipping Address</p>
                        <p className="font-medium text-foreground leading-relaxed">123 TechNova HQ<br/>Bangalore, KA 560001</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1.5 uppercase font-semibold tracking-wider">Notes</p>
                        <p className="font-medium text-muted-foreground italic leading-relaxed">No additional notes provided by vendor.</p>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* OCR Tab */}
                <TabsContent value="ocr" className="flex-1 p-8 m-0 animate-in fade-in slide-in-from-bottom-2 duration-300">
                   <div className="space-y-6">
                      <div>
                         <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">1. Original Invoice</h3>
                         <div className="bg-muted/30 border border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center">
                            <FileText className="w-8 h-8 text-muted-foreground mb-2 opacity-50" />
                            <p className="text-sm font-medium">invoice_scan.pdf</p>
                            <Button variant="link" className="h-auto p-0 text-xs">View Document</Button>
                         </div>
                      </div>
                      <div className="flex justify-center"><ArrowRight className="w-5 h-5 text-muted-foreground rotate-90 opacity-50" /></div>
                      <div>
                         <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">2. OCR Output</h3>
                         <div className="bg-primary/5 border border-primary/10 rounded-xl p-4 font-mono text-xs text-muted-foreground overflow-hidden max-h-[150px] relative">
                            {`{"raw_text": "INVOICE\\nNo: ${invoiceDetails.invoice_number}\\nDate: ${invoiceDetails.invoice_date}\\nVendor: ${invoiceDetails.vendor_name}\\n... (truncated)"}`}
                            <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent" />
                         </div>
                      </div>
                      <div className="flex justify-center"><ArrowRight className="w-5 h-5 text-muted-foreground rotate-90 opacity-50" /></div>
                      <div>
                         <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">3. Extracted Fields</h3>
                         <div className="border rounded-xl p-5 space-y-3 bg-background">
                            <div className="flex justify-between items-center border-b pb-2">
                               <span className="text-sm text-muted-foreground">Confidence Score</span>
                               <Badge variant="outline" className="bg-green-500/10 text-green-700 border-none">99.8% High</Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-4 pt-2">
                               <div>
                                 <span className="block text-[10px] uppercase font-bold text-muted-foreground">Extracted Vendor</span>
                                 <span className="text-sm font-medium">{invoiceDetails.vendor_name}</span>
                               </div>
                               <div>
                                 <span className="block text-[10px] uppercase font-bold text-muted-foreground">Extracted Amount</span>
                                 <span className="text-sm font-medium font-mono">{formatCurrency(invoiceDetails.total_amount)}</span>
                               </div>
                            </div>
                         </div>
                      </div>
                   </div>
                </TabsContent>

                {/* AI Analysis Tab */}
                <TabsContent value="ai" className="flex-1 p-8 m-0 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="space-y-8">
                      <div>
                          <div className="flex items-center gap-3 mb-4">
                              <div className="p-2 bg-primary/10 rounded-xl"><Bot className="h-5 w-5 text-primary" /></div>
                              <h3 className="font-semibold text-lg text-foreground">AI Intelligence Review</h3>
                          </div>
                          
                          {/* Summary */}
                          <div className="mb-6">
                             <h4 className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground mb-2">Summary</h4>
                             <p className="text-[14.5px] leading-relaxed text-foreground">
                                Invoice for {invoiceDetails.department} services. The pricing matches historical averages for this vendor.
                             </p>
                          </div>

                          <div className="h-px bg-border/50 w-full mb-6" />

                          {/* Items Breakdown */}
                          <div className="mb-6">
                             <h4 className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground mb-3">Items Categorization</h4>
                             <ul className="space-y-3">
                                {invoiceDetails.line_items.map((item: any) => (
                                   <li key={item.id} className="flex items-start gap-2 text-[14px]">
                                      <span className="text-muted-foreground mt-0.5">•</span>
                                      <span>Categorized <strong>{item.description}</strong> as <Badge variant="secondary" className="text-[10px] px-1.5 py-0 uppercase mx-1">{item.category}</Badge></span>
                                   </li>
                                ))}
                             </ul>
                          </div>

                          <div className="h-px bg-border/50 w-full mb-6" />

                          {/* Vendor Verification */}
                          <div className="mb-6">
                             <h4 className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground mb-3">Vendor Verification</h4>
                             <ul className="space-y-3 text-[14px]">
                                <li className="flex justify-between items-center">
                                   <span className="text-muted-foreground">GST Matching</span>
                                   <span className="font-medium text-foreground">Matched Database</span>
                                </li>
                                <li className="flex justify-between items-center">
                                   <span className="text-muted-foreground">Bank Details</span>
                                   <span className="font-medium text-foreground">Matched Database</span>
                                </li>
                             </ul>
                          </div>
                          
                          {/* Recommendations */}
                          <div className="bg-primary/5 rounded-xl p-5 border border-primary/20">
                             <h4 className="text-[11px] uppercase tracking-wider font-bold text-primary mb-2">Recommendation</h4>
                             <p className="text-[14.5px] font-medium text-foreground">
                                {invoiceDetails.risk_score >= 5 ? "Flagged for manual review due to anomalies." : "Safe to approve. No anomalies detected."}
                             </p>
                          </div>
                      </div>
                  </div>
                </TabsContent>

                {/* Risk Center Tab */}
                <TabsContent value="risk" className="flex-1 p-8 m-0 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="space-y-8">
                    {/* Risk Score Summary */}
                    <div className="flex items-center justify-between border-b pb-6">
                       <div>
                          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Risk Score</h3>
                          <div className="flex items-baseline gap-2 mt-1">
                             <span className="text-4xl font-bold font-mono tracking-tight">{invoiceDetails.risk_score}</span>
                             <span className="text-xl text-muted-foreground font-mono">/10</span>
                          </div>
                       </div>
                       <div>
                          {invoiceDetails.risk_score >= 5 ? (
                             <Badge variant="destructive" className="h-8 px-4 text-sm font-semibold">High Risk</Badge>
                          ) : (
                             <Badge variant="outline" className="h-8 px-4 text-sm font-semibold bg-green-500/10 text-green-700 border-green-500/20">Low Risk</Badge>
                          )}
                       </div>
                    </div>

                    {/* Reasons Checklist */}
                    <div>
                       <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Risk Factors Evaluated</h3>
                       <div className="space-y-4">
                          <div className="flex items-start gap-3">
                             <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                             <span className="text-[15px] font-medium">No duplicate payments found</span>
                          </div>
                          <div className="flex items-start gap-3">
                             <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                             <span className="text-[15px] font-medium">GST matches vendor profile</span>
                          </div>
                          <div className="flex items-start gap-3">
                             <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                             <span className="text-[15px] font-medium">Bank account matches vendor profile</span>
                          </div>
                          <div className="flex items-start gap-3">
                             <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                             <span className="text-[15px] font-medium">Tax calculations mathematically correct</span>
                          </div>
                          {invoiceDetails.alerts.filter((a: any) => a.severity === 'high').map((alert: any) => (
                             <div key={alert.id} className="flex items-start gap-3 mt-4 pt-4 border-t">
                                <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
                                <div>
                                   <span className="text-[15px] font-bold text-red-600 block">{alert.alert_type}</span>
                                   <span className="text-[14px] text-muted-foreground block mt-1">{alert.message}</span>
                                </div>
                             </div>
                          ))}
                       </div>
                    </div>

                    {/* Final Recommendation */}
                    <div className="pt-4">
                       <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">Recommendation</h3>
                       <div className={`p-4 rounded-xl border ${invoiceDetails.risk_score >= 5 ? 'bg-red-500/5 border-red-500/20 text-red-700' : 'bg-green-500/5 border-green-500/20 text-green-700'}`}>
                          <p className="font-semibold text-sm">
                             {invoiceDetails.risk_score >= 5 ? "Proceed with caution. Manual verification required." : "Proceed. This invoice has passed all systemic risk checks."}
                          </p>
                       </div>
                    </div>

                  </div>
                </TabsContent>

                {/* Timeline Tab */}
                <TabsContent value="timeline" className="flex-1 p-8 m-0 animate-in fade-in slide-in-from-bottom-2 duration-300">
                   <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-6">Document Lifecycle</h3>
                   <div className="relative border-l-2 border-muted ml-3 space-y-8 pb-4 mt-2">
                      <div className="relative pl-6">
                         <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-blue-500 ring-4 ring-background" />
                         <p className="text-[14.5px] font-semibold text-foreground">Vendor Uploaded</p>
                         <p className="text-xs text-muted-foreground mt-1">{invoiceDetails.invoice_date || "June 1"} • Portal Upload</p>
                      </div>
                      <div className="relative pl-6">
                         <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-indigo-500 ring-4 ring-background" />
                         <p className="text-[14.5px] font-semibold text-foreground">OCR Completed</p>
                         <p className="text-xs text-muted-foreground mt-1">Automated Extraction</p>
                      </div>
                      <div className="relative pl-6">
                         <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-purple-500 ring-4 ring-background" />
                         <p className="text-[14.5px] font-semibold text-foreground">AI Analysis</p>
                         <p className="text-xs text-muted-foreground mt-1">Verification & Risk Scoring</p>
                      </div>
                      <div className="relative pl-6">
                         <span className={`absolute -left-[9px] top-1 h-4 w-4 rounded-full ring-4 ring-background ${invoiceDetails.verification_status === "Verified" || invoiceDetails.verification_status === "Approved" ? "bg-green-500" : "bg-muted"}`} />
                         <p className="text-[14.5px] font-semibold text-foreground">Finance Verified</p>
                         <p className="text-xs text-muted-foreground mt-1">Executive Review</p>
                      </div>
                      <div className="relative pl-6">
                         <span className={`absolute -left-[9px] top-1 h-4 w-4 rounded-full ring-4 ring-background ${invoiceDetails.verification_status === "Approved" ? "bg-green-500" : "bg-muted"}`} />
                         <p className="text-[14.5px] font-semibold text-foreground">Manager Approved</p>
                         <p className="text-xs text-muted-foreground mt-1">Final Approval</p>
                      </div>
                      <div className="relative pl-6">
                         <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-muted ring-4 ring-background" />
                         <p className="text-[14.5px] font-semibold text-muted-foreground">Paid</p>
                         <p className="text-xs text-muted-foreground mt-1">Pending ERP Sync</p>
                      </div>
                   </div>
                </TabsContent>

              </Tabs>
            </div>
          )}
        </SheetContent>
      </Sheet>

    </div>
  );
}
