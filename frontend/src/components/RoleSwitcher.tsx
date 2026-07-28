"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { Building2, ShieldAlert } from "lucide-react";

interface Vendor {
  id: number;
  name: string;
}

export default function RoleSwitcher() {
  const { authState, setRole } = useAuth();
  const [vendors, setVendors] = useState<Vendor[]>([]);

  useEffect(() => {
    const fetchVendors = async () => {
      try {
        const res = await axios.get("http://localhost:8000/api/v1/auth/vendors");
        setVendors(res.data);
      } catch (err) {
        console.error("Failed to load vendors", err);
      }
    };
    fetchVendors();
  }, []);

  return (
    <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-lg shadow-sm border border-gray-100">
      <div className="text-sm font-semibold text-gray-500">View As:</div>
      <button
        onClick={() => setRole("admin")}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          authState.role === "admin" ? "bg-indigo-100 text-indigo-700" : "hover:bg-gray-100 text-gray-600"
        }`}
      >
        <ShieldAlert className="w-4 h-4" /> Admin
      </button>
      
      <div className="h-4 w-px bg-gray-300 mx-1"></div>
      
      <select
        className={`text-sm font-medium outline-none cursor-pointer rounded-md px-2 py-1.5 transition-colors ${
          authState.role === "vendor" ? "bg-emerald-100 text-emerald-700" : "hover:bg-gray-100 text-gray-600 bg-transparent"
        }`}
        value={authState.role === "vendor" ? authState.vendorId || "" : ""}
        onChange={(e) => {
          if (e.target.value) {
            setRole("vendor", e.target.value);
          }
        }}
      >
        <option value="" disabled>Select Vendor Portal</option>
        {vendors.map(v => (
          <option key={v.id} value={v.id.toString()}>
            {v.name}
          </option>
        ))}
      </select>
    </div>
  );
}
