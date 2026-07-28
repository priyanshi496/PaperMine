"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function Sidebar() {
  const pathname = usePathname();
  const { authState } = useAuth();

  if (!authState.user) return null;

  const navItems = [
    { name: "Dashboard", href: "/", icon: "dashboard", roles: ["admin", "vendor"] },
    { name: "Documents", href: "/documents", icon: "folder_open", roles: ["admin", "vendor"] },
    { name: "Vendors", href: "/vendors", icon: "groups", roles: ["admin"] },
    { name: "Analytics", href: "/analytics", icon: "monitoring", roles: ["admin"] },
    { name: "AI Assistant", href: "/assistant", icon: "smart_toy", roles: ["admin", "vendor"] },
    { name: "Settings", href: "/settings", icon: "settings", roles: ["admin", "vendor"] },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-[260px] bg-surface-container border-r border-outline-variant flex flex-col z-50">
      
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-outline-variant">
        <div className="flex items-center gap-2 text-primary">
          <span className="material-symbols-outlined text-[28px] text-secondary">category</span>
          <span className="font-sans font-bold text-[20px] tracking-tight text-on-surface">PaperMine</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 flex flex-col gap-1 overflow-y-auto">
        {navItems.filter(item => item.roles.includes(authState.user!.role)).map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link 
              key={item.name} 
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-[14px] font-medium font-sans ${
                isActive 
                  ? "bg-secondary-container text-on-secondary-container font-bold" 
                  : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
              }`}
            >
              <span className={`material-symbols-outlined text-[20px] ${isActive ? "text-secondary" : ""}`}>
                {item.icon}
              </span>
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Profile/System Status */}
      <div className="p-4 mt-auto border-t border-outline-variant">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-[13px]">
            {authState.user.email.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col">
            <span className="text-[13px] font-bold text-on-surface leading-tight max-w-[150px] truncate">{authState.user.email}</span>
            <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">{authState.user.role}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
