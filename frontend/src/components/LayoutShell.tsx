"use client";

import { useAuth } from "@/context/AuthContext";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import TopHeader from "@/components/TopHeader";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { authState, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !authState.token && pathname !== "/login" && pathname !== "/signup") {
      router.push("/login");
      return;
    }

    if (!loading && authState.user) {
      const role = authState.user.role;
      const isVendor = role === "vendor";
      
      if (isVendor) {
        if (pathname.startsWith("/operations") || pathname.startsWith("/analytics") || pathname.startsWith("/risk") || pathname === "/") {
          router.replace("/vendor/intelligence");
        }
      } else {
        if (pathname.startsWith("/vendor")) {
          router.replace("/");
        }
      }
    }
  }, [authState.token, authState.user, pathname, loading, router]);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        if (e.key === "Escape") {
          (document.activeElement as HTMLElement).blur();
        }
        return;
      }

      if (e.key === "/") {
        e.preventDefault();
        const searchInput = document.querySelector('input[placeholder*="Ask AI"]') as HTMLInputElement | null;
        searchInput?.focus();
      } else if (e.key === "A" && e.shiftKey) {
        e.preventDefault();
        router.push("/copilot");
      } else if (e.key === "u" || e.key === "U") {
        e.preventDefault();
        router.push("/operations/invoices");
      } else if (e.key === "Escape") {
        // Find any active Sheet overlay and click its close button or trigger Esc
        const closeBtn = document.querySelector('[data-state="open"] button[aria-label="Close"]') as HTMLButtonElement | null;
        closeBtn?.click();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router]);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-surface">
        <Loader2 className="w-8 h-8 animate-spin text-secondary" />
      </div>
    );
  }

  // If on login or signup page, render full screen without layout
  if (pathname === "/login" || pathname === "/signup") {
    return <main className="h-screen w-full">{children}</main>;
  }

  // Otherwise, render full application shell
  return (
    <div className="flex h-screen w-full">
      <Sidebar />
      <div className="flex-1 flex flex-col pl-[280px] h-screen overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto bg-background">
          {children}
        </main>
      </div>
    </div>
  );
}
