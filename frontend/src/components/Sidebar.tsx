"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  Layers,
  FileText,
  Users,
  Building2,
  BarChart3,
  PieChart,
  LineChart,
  Network,
  Bot,
  ShieldAlert,
  Settings,
  CreditCard,
  User,
  LogOut
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

type NavItem = {
  name: string;
  href: string;
  icon: any;
};

type NavGroup = {
  title: string;
  items: NavItem[];
};

export default function Sidebar() {
  const pathname = usePathname();
  const { authState, logout } = useAuth();

  if (!authState.user) return null;
  const isVendor = authState.user.role === "vendor";

  const companyNav: NavGroup[] = [
    {
      title: "Workspace",
      items: [{ name: "Overview", href: "/", icon: LayoutDashboard }],
    },
    {
      title: "Operations",
      items: [
        { name: "Invoice Operations", href: "/operations/invoices", icon: FileText },
        { name: "Vendor Hub", href: "/operations/vendors", icon: Users },
        { name: "Departments", href: "/operations/departments", icon: Building2 },
      ],
    },
    {
      title: "Intelligence",
      items: [
        { name: "Financial Intelligence", href: "/analytics/financial", icon: PieChart },
        { name: "Vendor Intelligence", href: "/analytics/vendor", icon: BarChart3 },
        { name: "Department Intelligence", href: "/analytics/department", icon: Network },
      ],
    },
    {
      title: "AI & Risk",
      items: [
        { name: "AI Copilot", href: "/copilot", icon: Bot },
        { name: "Risk Center", href: "/risk", icon: ShieldAlert },
      ],
    },
  ];

  const vendorNav: NavGroup[] = [
    {
      title: "Workspace",
      items: [{ name: "Overview", href: "/vendor/intelligence", icon: LayoutDashboard }],
    },
    {
      title: "Operations",
      items: [
        { name: "My Invoices", href: "/vendor/invoices", icon: FileText },
        { name: "Payments", href: "/vendor/payments", icon: CreditCard },
      ],
    },
    {
      title: "Intelligence",
      items: [
        { name: "Business Intelligence", href: "/vendor/intelligence", icon: BarChart3 },
        { name: "AI Advisor", href: "/vendor/advisor", icon: Bot },
      ],
    },
  ];

  const navGroups = isVendor ? vendorNav : companyNav;

  return (
    <aside className="fixed left-0 top-0 h-screen w-[280px] bg-background border-r flex flex-col z-50">
      
      {/* Logo */}
      <div className="h-16 flex items-center px-8 border-b">
        <div className="flex items-center gap-2 text-primary">
          <Layers className="w-6 h-6 text-primary" />
          <span className="font-bold text-lg tracking-tight">PaperMine</span>
        </div>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 py-4">
        <nav className="px-6 space-y-6">
          {navGroups.map((group, idx) => (
            <div key={idx} className="flex flex-col gap-1">
              <h4 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                {group.title}
              </h4>
              {group.items.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                // Exact match for root Overview
                const isExactActive = item.href === "/" ? pathname === "/" : isActive;

                return (
                  <Link 
                    key={item.name} 
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-2 py-2 rounded-md transition-all text-sm font-medium",
                      isExactActive 
                        ? "bg-primary/10 text-primary font-semibold" 
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <item.icon className={cn("w-4 h-4", isExactActive ? "text-primary" : "text-muted-foreground")} />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </ScrollArea>

      {/* Profile/System Status */}
      <div className="p-4 mt-auto border-t">
        <div className="flex items-center gap-3 px-4 py-2">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
            {authState.user.email.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col flex-1 overflow-hidden">
            <span className="text-sm font-semibold text-foreground truncate">{authState.user.email}</span>
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">{authState.user.role.replace('_', ' ')}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={logout} className="shrink-0 h-8 w-8 text-muted-foreground hover:text-foreground">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
