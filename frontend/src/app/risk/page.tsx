"use client";

import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, ShieldAlert, CheckCircle2, Clock } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDistanceToNow } from "date-fns";

export default function RiskCenter() {
  const { authState, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const filterParam = searchParams.get("filter");
  
  const [alerts, setAlerts] = useState<any[]>([]);
  const [filteredAlerts, setFilteredAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && authState.token) {
      fetchAlerts();
    }
  }, [authLoading, authState.token]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const res = await axios.get("http://localhost:8000/api/v1/insights/");
      const data = res.data;
      setAlerts(data);
      
      if (filterParam === "high") {
        setFilteredAlerts(data.filter((a: any) => a.severity === "high"));
      } else {
        setFilteredAlerts(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const highRiskCount = alerts.filter(a => a.severity === "high" && !a.resolved).length;
  const mediumRiskCount = alerts.filter(a => a.severity === "medium" && !a.resolved).length;
  const resolvedCount = alerts.filter(a => a.resolved).length;

  return (
    <div className="flex-1 p-8 space-y-8 max-w-7xl mx-auto pb-24">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <ShieldAlert className="h-8 w-8 text-red-500" />
          Risk Center
        </h1>
        <p className="text-muted-foreground mt-1">
          Monitor real-time fraud alerts, duplicates, and AI-detected anomalies.
        </p>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-6">
          <div className="h-32 bg-muted rounded-xl w-full"></div>
          <div className="h-64 bg-muted rounded-xl w-full"></div>
        </div>
      ) : (
        <>
          {/* Top Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="bg-red-500/5 border-red-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-red-600 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> High Severity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">{highRiskCount}</div>
                <p className="text-xs text-red-600/70 mt-1">Immediate action required</p>
              </CardContent>
            </Card>

            <Card className="bg-yellow-500/5 border-yellow-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-yellow-600 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> Medium Severity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-yellow-600">{mediumRiskCount}</div>
                <p className="text-xs text-yellow-600/70 mt-1">Review recommended</p>
              </CardContent>
            </Card>

            <Card className="bg-green-500/5 border-green-500/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-green-600 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> Resolved Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{resolvedCount}</div>
                <p className="text-xs text-green-600/70 mt-1">Successfully handled</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Timeline View */}
            <div className="lg:col-span-1">
              <h3 className="font-semibold text-lg mb-4">Live Threat Timeline</h3>
              <div className="relative border-l border-muted-foreground/20 ml-3 space-y-6">
                {alerts.slice(0, 8).map((alert, idx) => (
                  <div key={idx} className="relative pl-6">
                    <div className={`absolute -left-[5px] top-1 h-2.5 w-2.5 rounded-full ${alert.severity === 'high' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-yellow-500'}`}></div>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {alert.created_at ? formatDistanceToNow(new Date(alert.created_at), { addSuffix: true }) : "Just now"}
                    </p>
                    <p className="text-sm font-medium mt-1">{alert.alert_type} detected</p>
                    <p className="text-xs text-muted-foreground">Vendor: {alert.vendor_name}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Detailed Table */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Alert Directory</CardTitle>
                  <CardDescription>
                    {filterParam === "high" ? "Filtering by High Severity" : "All system generated risk alerts."}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader className="bg-muted/50">
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Vendor</TableHead>
                        <TableHead>Invoice</TableHead>
                        <TableHead>Severity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredAlerts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center h-24">No alerts found.</TableCell>
                        </TableRow>
                      ) : (
                        filteredAlerts.map(alert => (
                          <TableRow key={alert.id}>
                            <TableCell className="font-medium text-sm">{alert.alert_type}</TableCell>
                            <TableCell className="text-sm">{alert.vendor_name}</TableCell>
                            <TableCell className="text-sm text-muted-foreground">{alert.invoice_number}</TableCell>
                            <TableCell>
                              <Badge variant={alert.severity === 'high' ? 'destructive' : 'secondary'}>
                                {alert.severity}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
