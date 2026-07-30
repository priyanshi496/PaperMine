"use client";

import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, BarChart, Bar
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DollarSign, FileText, HeartPulse, AlertTriangle, ArrowRight, Bot, Clock, ShieldCheck, Activity, Users, Zap, Search } from "lucide-react";
import { Input } from "@/components/ui/input";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Filter } from "lucide-react";
import { usePageContext } from "@/context/PageContext";

export default function OverviewDashboard() {
  const { authState, loading: authLoading } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const { setPageContext } = usePageContext();

  // Mock states for UI
  const [presentationMode, setPresentationMode] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("This Month");

  useEffect(() => {
    if (!authLoading && authState.token) {
      fetchDashboardData();
    }
  }, [authLoading, authState.token, dateFilter]); // Added dateFilter to dependency to mock re-fetching

  useEffect(() => {
    setPageContext({ page: "Financial Dashboard", date_filter: dateFilter });
  }, [dateFilter, setPageContext]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const res = await axios.get("http://localhost:8000/api/v1/dashboard/overview");
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex-1 p-8 space-y-6 animate-pulse">
        <div className="h-10 w-48 bg-muted rounded"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-32 bg-muted rounded-xl"></div>
          ))}
        </div>
        <div className="h-64 bg-muted rounded-xl"></div>
      </div>
    );
  }

  const { kpis, monthly_spend, department_spend, vendor_spend, recent_activity } = data;
  const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(val);

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };
  
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  // Mock Vendor Health
  const vendorHealth = { healthy: kpis.vendors > 0 ? kpis.vendors - 1 : 0, attention: kpis.vendors > 0 ? 1 : 0 };

  return (
    <div className={`flex-1 p-8 space-y-10 max-w-7xl mx-auto pb-24 ${presentationMode ? 'scale-[1.02] origin-top' : 'transition-transform duration-500'}`}>
      
      {/* Header & Presentation Toggle */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            Financial Dashboard
            <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20">Executive View</Badge>
          </h1>
          <p className="text-muted-foreground mt-1">
            Welcome back, {authState.user?.email.split('@')[0]}. Here is your real-time financial intelligence.
          </p>
        </div>
        <div className="flex gap-3">
            <Select value={dateFilter} onValueChange={setDateFilter}>
              <SelectTrigger className="w-[160px] bg-background">
                <Filter className="w-4 h-4 mr-2 text-muted-foreground" />
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Today">Today</SelectItem>
                <SelectItem value="This Week">This Week</SelectItem>
                <SelectItem value="This Month">This Month</SelectItem>
                <SelectItem value="Quarter">Quarter</SelectItem>
                <SelectItem value="YTD">YTD</SelectItem>
                <SelectItem value="Custom">Custom</SelectItem>
              </SelectContent>
            </Select>

            <Button variant={presentationMode ? "default" : "outline"} onClick={() => setPresentationMode(!presentationMode)} className="gap-2">
              <Zap className="w-4 h-4" /> Presentation Mode
            </Button>
        </div>
      </motion.div>

      {/* Ask AI Context */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className="relative max-w-2xl">
           <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
           <Input 
             placeholder="Ask AI: 'Why did IT spend increase last month?' or 'Show me Dell invoices'" 
             className="pl-10 rounded-full bg-background border-primary/20 focus-visible:ring-primary/30 h-12 shadow-sm"
             value={aiQuery}
             onChange={(e) => setAiQuery(e.target.value)}
             onKeyDown={(e) => {
               if (e.key === 'Enter' && aiQuery.trim()) {
                 router.push(`/copilot?q=${encodeURIComponent(aiQuery)}`);
               }
             }}
           />
           <Button 
             className="absolute right-1.5 top-1.5 h-9 rounded-full px-4" 
             size="sm"
             onClick={() => {
               if (aiQuery.trim()) {
                 router.push(`/copilot?q=${encodeURIComponent(aiQuery)}`);
               }
             }}
           >Ask</Button>
        </div>
      </motion.div>

      {/* Section 1: Executive KPIs */}
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        
        {/* Total Spend KPI */}
        <motion.div variants={item} onClick={() => router.push("/operations/invoices")} className="cursor-pointer">
          <Card className="hover:border-primary/50 transition-colors shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total Spend</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono tracking-tight">
                ₹<CountUp end={kpis.total_spend} separator="," duration={2} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Pending Payments KPI */}
        <motion.div variants={item} onClick={() => router.push("/operations/invoices")} className="cursor-pointer">
          <Card className="hover:border-yellow-500/50 transition-colors shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Pending Approval</CardTitle>
              <Clock className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono tracking-tight text-yellow-700 dark:text-yellow-500">
                 {kpis.pending} <span className="text-sm font-sans font-medium text-muted-foreground">invoices</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Business Health KPI */}
        <motion.div variants={item}>
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Business Health</CardTitle>
              <HeartPulse className={`h-4 w-4 ${kpis.health_score > 80 ? 'text-green-500' : 'text-yellow-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold flex items-center gap-2">
                <CountUp end={kpis.health_score} duration={2} />%
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* High Risk KPI */}
        <motion.div variants={item} onClick={() => router.push("/risk")} className="cursor-pointer">
          <Card className="hover:border-red-500/50 transition-colors bg-red-500/5 border-red-500/20 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-red-600/80">High Risk</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-700 dark:text-red-500">
                <CountUp end={kpis.high_risk} duration={2} /> <span className="text-sm font-medium opacity-80 font-sans">invoices</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Vendor Health KPI */}
        <motion.div variants={item} onClick={() => router.push("/operations/vendors")} className="cursor-pointer">
          <Card className="hover:border-primary/50 transition-colors shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Vendor Health</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold flex gap-2">
                 <span className="text-green-600">{vendorHealth.healthy}</span>
                 <span className="text-muted-foreground text-sm font-medium">/</span>
                 <span className="text-red-500">{vendorHealth.attention}</span>
              </div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1">Healthy / Attention</p>
            </CardContent>
          </Card>
        </motion.div>

      </motion.div>

      {/* Section 2: AI Executive Brief & Recommended Actions */}
      <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Executive Brief */}
        <div className="lg:col-span-2 bg-gradient-to-br from-primary/10 via-primary/5 to-background border border-primary/20 rounded-2xl p-8 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 bg-primary/10 rounded-xl shadow-inner">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-bold text-xl text-foreground flex items-center gap-3">
                Today's Executive Brief
                <Badge variant="secondary" className="bg-primary/20 text-primary hover:bg-primary/30 border-none px-2 rounded-full text-xs">Live AI Analysis</Badge>
              </h3>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
             <ul className="space-y-4 text-[15px] text-muted-foreground font-medium">
               <li className="flex items-start gap-3">
                 <ShieldCheck className="w-5 h-5 text-green-600 shrink-0" />
                 <span><strong className="text-foreground">{kpis.pending} invoices</strong> require finance approval today.</span>
               </li>
               <li className="flex items-start gap-3">
                 {kpis.high_risk > 0 ? <AlertTriangle className="w-5 h-5 text-yellow-600 shrink-0" /> : <ShieldCheck className="w-5 h-5 text-green-600 shrink-0" />}
                 <span><strong className="text-foreground">{kpis.high_risk} high-risk anomalies</strong> detected across recent transactions.</span>
               </li>
             </ul>
             <ul className="space-y-4 text-[15px] text-muted-foreground font-medium">
               <li className="flex items-start gap-3">
                 <Activity className="w-5 h-5 text-blue-500 shrink-0" />
                 <span>IT spending increased <strong className="text-foreground">18%</strong> month-over-month.</span>
               </li>
               <li className="flex items-start gap-3">
                 <Users className="w-5 h-5 text-purple-500 shrink-0" />
                 <span><strong className="text-foreground">Dell Technologies</strong> remains your highest-spend vendor this quarter.</span>
               </li>
             </ul>
          </div>
        </div>

        {/* AI Recommended Actions */}
        <div className="lg:col-span-1 bg-white dark:bg-surface border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-5">
            <Zap className="h-5 w-5 text-yellow-500" />
            <h3 className="font-bold text-[17px] text-foreground">AI Recommended Actions</h3>
          </div>
          <div className="space-y-3 flex-1">
             <div onClick={() => router.push("/operations/invoices")} className="group p-3 rounded-lg border border-border hover:border-primary/40 bg-muted/20 hover:bg-primary/5 cursor-pointer transition-all flex justify-between items-center">
                <div>
                  <p className="text-xs font-bold text-red-500 uppercase tracking-wider">Review</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5 group-hover:text-primary transition-colors">Metro Invoice (GST Mismatch)</p>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
             </div>
             <div onClick={() => router.push("/operations/invoices")} className="group p-3 rounded-lg border border-border hover:border-primary/40 bg-muted/20 hover:bg-primary/5 cursor-pointer transition-all flex justify-between items-center">
                <div>
                  <p className="text-xs font-bold text-green-600 uppercase tracking-wider">Approve</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5 group-hover:text-primary transition-colors">{kpis.pending} Pending Invoices</p>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
             </div>
             <div onClick={() => router.push("/copilot")} className="group p-3 rounded-lg border border-border hover:border-primary/40 bg-muted/20 hover:bg-primary/5 cursor-pointer transition-all flex justify-between items-center">
                <div>
                  <p className="text-xs font-bold text-blue-500 uppercase tracking-wider">Generate</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5 group-hover:text-primary transition-colors">Monthly Financial Report</p>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
             </div>
          </div>
        </div>
      </motion.div>

      {/* Section 3: Financial Charts */}
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Monthly Trend AreaChart */}
        <motion.div variants={item}>
          <Card className="h-[400px] shadow-sm border-muted">
            <CardHeader>
              <CardTitle>Monthly Spend</CardTitle>
              <CardDescription>Capital outflow across all departments over time</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthly_spend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={(value) => `₹${value/1000}k`} />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), "Spend"]}
                    contentStyle={{ borderRadius: "12px", border: "1px solid hsl(var(--border))", backgroundColor: "hsl(var(--background))", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                  />
                  <Area type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorAmount)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Top Vendors BarChart */}
        <motion.div variants={item}>
          <Card className="h-[400px] shadow-sm border-muted cursor-pointer hover:border-primary/50 transition-colors" onClick={() => router.push('/operations/vendors')}>
            <CardHeader>
              <CardTitle>Top Vendors</CardTitle>
              <CardDescription>Highest concentration of capital by vendor</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={vendor_spend} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={(value) => `₹${value/1000}k`} />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'hsl(var(--foreground))' }} width={120} />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), "Spend"]}
                    cursor={{fill: 'hsl(var(--muted)/0.5)'}}
                    contentStyle={{ borderRadius: "12px", border: "1px solid hsl(var(--border))", backgroundColor: "hsl(var(--background))" }}
                  />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Department PieChart */}
        <motion.div variants={item}>
          <Card className="h-[400px] shadow-sm border-muted cursor-pointer hover:border-primary/50 transition-colors" onClick={() => router.push('/operations/departments')}>
            <CardHeader>
              <CardTitle>Department Spend</CardTitle>
              <CardDescription>Allocation breakdown</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={department_spend}
                    innerRadius={70}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {department_spend.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number) => formatCurrency(value)} 
                    contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
                  />
                  <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '13px', paddingTop: '20px' }} iconType="circle"/>
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
        
        {/* Approval Funnel Mock */}
        <motion.div variants={item}>
          <Card className="h-[400px] shadow-sm border-muted">
            <CardHeader>
              <CardTitle>Approval Funnel</CardTitle>
              <CardDescription>Invoice lifecycle progression this month</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex flex-col justify-center px-8 space-y-6">
                <div className="w-full bg-muted/50 rounded-lg p-4 flex justify-between items-center relative overflow-hidden">
                   <div className="absolute left-0 top-0 bottom-0 bg-blue-500/20 w-full rounded-lg" />
                   <span className="font-semibold z-10">1. Uploaded / OCR</span>
                   <span className="font-mono font-bold z-10">{kpis.invoices}</span>
                </div>
                <div className="w-[85%] mx-auto bg-muted/50 rounded-lg p-4 flex justify-between items-center relative overflow-hidden">
                   <div className="absolute left-0 top-0 bottom-0 bg-indigo-500/20 w-full rounded-lg" />
                   <span className="font-semibold z-10">2. AI Verified</span>
                   <span className="font-mono font-bold z-10">{Math.max(0, kpis.invoices - kpis.high_risk)}</span>
                </div>
                <div className="w-[70%] mx-auto bg-muted/50 rounded-lg p-4 flex justify-between items-center relative overflow-hidden">
                   <div className="absolute left-0 top-0 bottom-0 bg-purple-500/20 w-full rounded-lg" />
                   <span className="font-semibold z-10">3. Finance Approved</span>
                   <span className="font-mono font-bold z-10">{Math.max(0, kpis.invoices - kpis.pending)}</span>
                </div>
                <div className="w-[55%] mx-auto bg-muted/50 rounded-lg p-4 flex justify-between items-center relative overflow-hidden">
                   <div className="absolute left-0 top-0 bottom-0 bg-green-500/20 w-full rounded-lg" />
                   <span className="font-semibold z-10">4. Paid</span>
                   <span className="font-mono font-bold z-10">{Math.max(0, kpis.invoices - kpis.pending - 4)}</span>
                </div>
            </CardContent>
          </Card>
        </motion.div>

      </motion.div>

      {/* Section 4: Recent Financial Activity (Timeline Flow) */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Timeline */}
          <Card className="lg:col-span-1 shadow-sm border-muted bg-background">
            <CardHeader>
              <CardTitle>Recent Financial Activity</CardTitle>
              <CardDescription>Live feed of document processing</CardDescription>
            </CardHeader>
            <CardContent>
               <div className="relative border-l-2 border-muted ml-3 space-y-8 pb-4 mt-2">
                  <div className="relative pl-6">
                     <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-blue-500 ring-4 ring-background" />
                     <p className="text-sm font-semibold text-foreground">Metro Wholesale uploaded invoice</p>
                     <p className="text-xs text-muted-foreground mt-1">09:30 AM • MTR-2026-6666</p>
                  </div>
                  <div className="relative pl-6">
                     <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-indigo-500 ring-4 ring-background" />
                     <p className="text-sm font-semibold text-foreground">PaperMine AI Extracted Data</p>
                     <p className="text-xs text-muted-foreground mt-1">09:45 AM • 100% confidence</p>
                  </div>
                  <div className="relative pl-6">
                     <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-purple-500 ring-4 ring-background" />
                     <p className="text-sm font-semibold text-foreground">AI Risk Verification</p>
                     <p className="text-xs text-muted-foreground mt-1">09:47 AM • Passed all checks</p>
                  </div>
                  <div className="relative pl-6">
                     <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-yellow-500 ring-4 ring-background" />
                     <p className="text-sm font-semibold text-foreground">Needs Manager Approval</p>
                     <p className="text-xs text-muted-foreground mt-1">10:10 AM • Routed to Finance Team</p>
                  </div>
               </div>
            </CardContent>
          </Card>

          {/* Attention Required Invoices */}
          <Card className="lg:col-span-2 shadow-sm border-muted">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-red-600 dark:text-red-400">Attention Required</CardTitle>
                <CardDescription>Invoices requiring immediate executive action.</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push("/operations/invoices")} className="text-foreground">
                Go to Inbox <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recent_activity && recent_activity.filter((a: any) => a.risk_score >= 5 || a.status === 'Needs Manager Approval').slice(0, 5).map((activity: any) => (
                  <div key={activity.id} className="flex items-center justify-between p-4 rounded-xl border hover:border-primary/50 hover:bg-muted/30 transition-all cursor-pointer group shadow-sm" onClick={() => router.push(`/operations/invoices?id=${activity.id}`)}>
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm shrink-0">
                        {activity.vendor_name.charAt(0)}
                      </div>
                      <div>
                        <h4 className="font-semibold text-[14.5px] group-hover:text-primary transition-colors">{activity.vendor_name}</h4>
                        <p className="text-xs text-muted-foreground mt-1 font-mono">{activity.invoice_number} • {activity.date}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      {activity.risk_score >= 5 ? (
                        <Badge variant="destructive" className="shadow-sm"><AlertTriangle className="w-3 h-3 mr-1"/>High Risk</Badge>
                      ) : (
                        <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700 border-yellow-500/20 shadow-sm">{activity.status}</Badge>
                      )}
                      <span className="font-mono font-bold text-[15px]">{formatCurrency(activity.amount)}</span>
                    </div>
                  </div>
                ))}
                {(!recent_activity || recent_activity.filter((a: any) => a.risk_score >= 5 || a.status === 'Needs Manager Approval').length === 0) && (
                   <div className="text-center p-8 text-muted-foreground">
                      <ShieldCheck className="w-12 h-12 mx-auto text-green-500 mb-3 opacity-50" />
                      <p>All clear. No invoices require your immediate attention.</p>
                   </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

    </div>
  );
}
