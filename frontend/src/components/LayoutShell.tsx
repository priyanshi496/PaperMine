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
    }
  }, [authState.token, pathname, loading, router]);

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
