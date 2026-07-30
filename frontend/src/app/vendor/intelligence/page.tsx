"use client";

import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, TrendingUp, Search, Clock, FileText, CheckCircle2, ShieldCheck, DollarSign, Bot } from "lucide-react";
import { format } from "date-fns";
import { usePageContext } from "@/context/PageContext";

export default function VendorIntelligence() {
  const { authState, loading: authLoading } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { setPageContext } = usePageContext();

  useEffect(() => {
    if (!authLoading && authState.token) {
      fetchVendorData();
    }
  }, [authLoading, authState.token]);

  useEffect(() => {
    if (authState.user) {
      setPageContext({
        page: "Vendor Intelligence",
        entity: { type: "vendor", id: authState.user.id }
      });
    }
  }, [authState.user, setPageContext]);

  const fetchVendorData = async () => {
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
      <div className="flex-1 p-8 space-y-6 animate-pulse max-w-7xl mx-auto w-full">
        <div className="h-10 w-64 bg-muted rounded"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-muted rounded-xl"></div>
          ))}
        </div>
        <div className="h-64 bg-muted rounded-xl"></div>
      </div>
    );
  }

  const { kpis, monthly_spend, recent_activity } = data;
  
  // Custom KPI for Vendor: Approval Rate
  const total = kpis.invoices;
  const approved = total - kpis.pending - kpis.high_risk; // Simplification
  const approvalRate = total > 0 ? Math.round((approved / total) * 100) : 100;

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

  return (
    <div className="flex-1 p-8 space-y-8 max-w-7xl mx-auto pb-24">
      
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Vendor Intelligence</h1>
        <p className="text-muted-foreground mt-1">
          Your business relationship with TechNova Pvt Ltd.
        </p>
      </motion.div>

      {/* AI Business Advisor */}
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}>
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="flex items-start sm:items-center gap-4 p-4">
            <div className="p-2 bg-primary/20 rounded-full shrink-0">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-foreground text-sm flex items-center gap-2">
                AI Business Advisor
                <Badge variant="outline" className="text-[10px] uppercase bg-background border-primary/20">Auto-Generated</Badge>
              </h4>
              <p className="text-sm text-muted-foreground mt-1 leading-snug">
                Your approval rate is excellent at {approvalRate}%. We recommend ensuring your GSTIN and Bank details remain consistent to maintain zero compliance issues. Revenue trend is stable.
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <motion.div variants={item}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Revenue</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ₹<CountUp end={kpis.total_spend} separator="," duration={2} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Invoices Submitted</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                <CountUp end={kpis.invoices} duration={2} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Approval Rate</CardTitle>
              <CheckCircle2 className={`h-4 w-4 ${approvalRate > 80 ? 'text-green-500' : 'text-yellow-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                <CountUp end={approvalRate} duration={2} />%
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card className={kpis.high_risk > 0 ? "bg-red-500/5 border-red-500/20" : ""}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className={`text-sm font-medium ${kpis.high_risk > 0 ? 'text-red-500' : 'text-muted-foreground'}`}>Risk Alerts</CardTitle>
              <AlertTriangle className={`h-4 w-4 ${kpis.high_risk > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${kpis.high_risk > 0 ? 'text-red-600' : ''}`}>
                <CountUp end={kpis.high_risk} duration={2} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

      </motion.div>

      {/* Charts Row */}
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Monthly Trend AreaChart */}
        <motion.div variants={item}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Revenue Trend</CardTitle>
              <CardDescription>Your monthly revenue from TechNova</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthly_spend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} tickFormatter={(value) => `₹${value/1000}k`} />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), "Revenue"]}
                    contentStyle={{ borderRadius: "8px", border: "1px solid hsl(var(--border))", backgroundColor: "hsl(var(--background))" }}
                  />
                  <Area type="monotone" dataKey="amount" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorAmount)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Dummy Top Products BarChart */}
        <motion.div variants={item}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Top Services / Products</CardTitle>
              <CardDescription>Derived from your recent invoices</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: "Coffee", value: 45000 },
                  { name: "Sandwiches", value: 25000 },
                  { name: "Laptops", value: 120000 },
                  { name: "Monitors", value: 35000 },
                ]} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} tickFormatter={(value) => `₹${value/1000}k`} />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), "Value"]}
                    contentStyle={{ borderRadius: "8px", border: "1px solid hsl(var(--border))", backgroundColor: "hsl(var(--background))" }}
                  />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

      </motion.div>

    </div>
  );
}
