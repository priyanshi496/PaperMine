"use client";

import VendorInvoicesTable from "@/components/VendorInvoicesTable";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Trash2, Plus, Loader2, UserPlus } from "lucide-react";

export default function VendorsPage() {
  const { authState } = useAuth();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const [vendors, setVendors] = useState<any[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newVendorName, setNewVendorName] = useState("");
  const [newVendorGstin, setNewVendorGstin] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const fetchVendors = () => {
    axios.get("http://localhost:8000/api/v1/auth/vendors").then(res => setVendors(res.data));
  };

  useEffect(() => {
    setMounted(true);
    if (authState.user?.role === "admin") {
      fetchVendors();
    }
  }, [authState]);

  const handleAddVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAdding(true);
    try {
      await axios.post("http://localhost:8000/api/v1/auth/vendors", {
        name: newVendorName,
        gstin: newVendorGstin
      });
      setShowAddModal(false);
      setNewVendorName("");
      setNewVendorGstin("");
      fetchVendors();
    } catch (err) {
      console.error(err);
      alert("Failed to add vendor");
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteVendor = async (id: number) => {
    if (!confirm("Are you sure you want to delete this vendor and their account?")) return;
    try {
      await axios.delete(`http://localhost:8000/api/v1/auth/vendors/${id}`);
      fetchVendors();
    } catch (err) {
      console.error(err);
      alert("Failed to delete vendor");
    }
  };

  if (!mounted || !authState.user) return null;

  if (authState.user.role !== "admin") {
    return <div className="p-8 text-error">Access Denied</div>;
  }

  return (
    <div className="pt-16 min-h-screen p-8 max-w-[1600px] mx-auto animate-in fade-in duration-500 relative">
      
      <section className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="font-sans text-[36px] font-bold text-on-surface leading-[44px] tracking-[-0.02em] mb-1">
            Vendor Management
          </h1>
          <p className="font-sans text-[14px] text-on-surface-variant">
            Manage your vendors and review all incoming invoices.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-8">
        
        <div className="flex flex-col gap-4">
            <div className="flex justify-between items-center">
                <h2 className="font-sans text-[18px] font-semibold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary">groups</span>
                  Registered Vendors
                </h2>
                <button 
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-2 bg-primary text-on-primary font-mono text-[13px] px-4 py-2 rounded-lg hover:bg-on-primary-fixed-variant transition-colors"
                >
                  <Plus className="w-4 h-4" /> Add Vendor
                </button>
            </div>
            
            <div className="bg-white border border-outline-variant rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-[13px] font-sans">
                <thead className="bg-surface-container-low border-b border-outline-variant">
                    <tr>
                        <th className="px-6 py-4 font-bold text-on-surface-variant uppercase tracking-wider text-[11px] font-mono">ID</th>
                        <th className="px-6 py-4 font-bold text-on-surface-variant uppercase tracking-wider text-[11px] font-mono">Name</th>
                        <th className="px-6 py-4 font-bold text-on-surface-variant uppercase tracking-wider text-[11px] font-mono">GSTIN</th>
                        <th className="px-6 py-4 font-bold text-on-surface-variant uppercase tracking-wider text-[11px] font-mono">Status</th>
                        <th className="px-6 py-4 font-bold text-on-surface-variant uppercase tracking-wider text-[11px] font-mono text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                    {vendors.map(v => (
                        <tr key={v.id} className="hover:bg-surface-container-low/50 transition-colors group">
                            <td className="px-6 py-4 text-on-surface-variant font-mono">{v.id}</td>
                            <td className="px-6 py-4 font-medium text-on-surface flex items-center gap-2">
                              <div className="w-6 h-6 rounded bg-primary-container text-on-primary-container flex items-center justify-center font-bold text-[10px]">
                                {v.name.charAt(0)}
                              </div>
                              {v.name}
                            </td>
                            <td className="px-6 py-4 text-on-surface-variant font-mono text-[12px]">{v.gstin || "N/A"}</td>
                            <td className="px-6 py-4">
                                <span className="bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-[10px] font-bold tracking-wide uppercase border border-emerald-100">Active</span>
                            </td>
                            <td className="px-6 py-4 text-right">
                              <button 
                                onClick={() => handleDeleteVendor(v.id)}
                                className="text-error hover:bg-error-container p-2 rounded transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                                title="Delete Vendor"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                        </tr>
                    ))}
                    {vendors.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-8 text-on-surface-variant">No vendors found.</td>
                      </tr>
                    )}
                </tbody>
              </table>
            </div>
        </div>

        <div className="flex flex-col gap-4">
             <h2 className="font-sans text-[18px] font-semibold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">receipt_long</span>
              Global Invoice Ledger
            </h2>
             <div className="bg-white border border-outline-variant rounded-xl overflow-hidden min-h-[500px]">
                <VendorInvoicesTable />
             </div>
        </div>
      </div>

      {/* Add Vendor Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-outline-variant w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-low flex justify-between items-center">
              <h3 className="font-sans font-bold text-on-surface flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-secondary" /> Add New Vendor
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-on-surface-variant hover:text-error transition-colors">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <form onSubmit={handleAddVendor} className="p-6 space-y-4">
              <div className="space-y-1">
                <label className="font-mono text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Vendor Name</label>
                <input 
                  type="text"
                  required
                  value={newVendorName}
                  onChange={e => setNewVendorName(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded focus:ring-1 focus:ring-secondary focus:border-secondary outline-none text-sm transition-all"
                  placeholder="Acme Corp"
                />
              </div>
              <div className="space-y-1">
                <label className="font-mono text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">GSTIN / Tax ID (Optional)</label>
                <input 
                  type="text"
                  value={newVendorGstin}
                  onChange={e => setNewVendorGstin(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded focus:ring-1 focus:ring-secondary focus:border-secondary outline-none text-sm transition-all"
                  placeholder="29ABCDE1234F1Z5"
                />
              </div>
              
              <div className="bg-secondary-container/30 border border-secondary-container p-3 rounded-lg mt-4 text-[12px] text-on-surface-variant flex items-start gap-2">
                <span className="material-symbols-outlined text-[16px] text-secondary mt-0.5">info</span>
                <p>Creating this vendor will automatically generate a user account for them using the email format <span className="font-mono text-[10px] bg-white px-1 py-0.5 rounded border border-outline-variant">name@vendor.com</span> with password <span className="font-mono text-[10px] bg-white px-1 py-0.5 rounded border border-outline-variant">vendor123</span>.</p>
              </div>

              <div className="pt-4 flex gap-3 justify-end">
                <button type="button" onClick={() => setShowAddModal(false)} className="px-4 py-2 font-mono text-[12px] font-medium text-on-surface hover:bg-surface-container transition-colors rounded">Cancel</button>
                <button disabled={isAdding} type="submit" className="flex items-center gap-2 bg-primary text-on-primary font-mono text-[12px] px-5 py-2 rounded shadow-sm hover:bg-on-primary-fixed-variant transition-colors disabled:opacity-70">
                  {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create Vendor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
