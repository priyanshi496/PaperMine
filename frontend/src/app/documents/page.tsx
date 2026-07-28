"use client";

import FileUpload from "@/components/FileUpload";
import VendorInvoicesTable from "@/components/VendorInvoicesTable";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";

export default function DocumentsPage() {
  const { authState } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !authState.user) return null;

  return (
    <div className="pt-16 min-h-screen p-8 max-w-[1600px] mx-auto animate-in fade-in duration-500">
      
      <section className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="font-sans text-[36px] font-bold text-on-surface leading-[44px] tracking-[-0.02em] mb-1">
            Documents Hub
          </h1>
          <p className="font-sans text-[14px] text-on-surface-variant">
            Upload and manage your invoices here.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-8">
        
        <div className="flex flex-col gap-4">
            <h2 className="font-sans text-[18px] font-semibold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">upload_file</span>
              Submit New Invoice
            </h2>
            <div className="bg-white border border-outline-variant p-6 rounded-xl shadow-sm">
              <FileUpload />
            </div>
        </div>

        <div className="flex flex-col gap-4">
             <h2 className="font-sans text-[18px] font-semibold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">receipt_long</span>
              Invoice History
            </h2>
             <div className="bg-white border border-outline-variant rounded-xl overflow-hidden min-h-[500px]">
                <VendorInvoicesTable />
             </div>
        </div>

      </div>

    </div>
  );
}
