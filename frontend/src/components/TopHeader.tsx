"use client";

import { useAuth } from "@/context/AuthContext";
import { LogOut } from "lucide-react";

export default function TopHeader() {
  const { authState, logout } = useAuth();
  
  if (!authState.user) return null;

  return (
    <header className="fixed top-0 right-0 w-[calc(100%-260px)] h-16 bg-surface flex justify-between items-center px-4 border-b border-outline-variant z-40">
      
      {/* Search Bar */}
      <div className="flex items-center flex-1 max-w-xl">
        <div className="relative w-full focus-within:ring-1 focus-within:ring-secondary rounded-lg">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[13px]">search</span>
          <input 
            className="w-full bg-surface-container-low border-none rounded-lg pl-10 pr-4 py-2 text-[13px] font-sans focus:ring-0 outline-none" 
            placeholder="Search intel, documents, or vendors..." 
            type="text"
          />
        </div>
      </div>

      {/* Right Side Actions & Profile */}
      <div className="flex items-center gap-4">
        
        <div className="flex items-center gap-2 mr-4 border-r border-outline-variant pr-4">
            <span className="text-[12px] font-sans text-on-surface-variant font-medium">
                {authState.user.email}
            </span>
            <span className="bg-primary-container text-on-primary-container px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider font-bold">
                {authState.user.role}
            </span>
        </div>

        <button className="text-on-surface-variant hover:text-primary transition-all p-2 rounded-full hover:bg-surface-container-high">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="text-on-surface-variant hover:text-primary transition-all p-2 rounded-full hover:bg-surface-container-high">
          <span className="material-symbols-outlined">history</span>
        </button>
        
        <button 
            onClick={logout}
            title="Logout"
            className="text-error hover:bg-error-container transition-all p-2 rounded-full ml-2 flex items-center justify-center"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
