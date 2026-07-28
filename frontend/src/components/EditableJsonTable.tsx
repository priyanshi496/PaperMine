"use client";

import { useState } from "react";
import { Save, Plus, Trash2, Check } from "lucide-react";
import axios from "axios";

interface EditableJsonTableProps {
  documentId: string | number;
  initialJsonStr: string | null;
  onSaveSuccess: () => void;
}

export default function EditableJsonTable({ documentId, initialJsonStr, onSaveSuccess }: EditableJsonTableProps) {
  const [data, setData] = useState<any>(() => {
    if (!initialJsonStr) return {};
    try {
      return JSON.parse(initialJsonStr);
    } catch (e) {
      return {};
    }
  });
  
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "success" | "error">("idle");

  const handleFieldChange = (key: string, value: any) => {
    setData((prev: any) => {
      const prevVal = prev[key];
      if (prevVal && typeof prevVal === 'object' && 'value' in prevVal) {
        return { ...prev, [key]: { ...prevVal, value: value } };
      }
      return { ...prev, [key]: value };
    });
  };

  const handleLineItemChange = (index: number, key: string, value: any) => {
    setData((prev: any) => {
      const newLineItems = [...(prev.line_items || [])];
      const prevItemVal = newLineItems[index][key];
      
      if (prevItemVal && typeof prevItemVal === 'object' && 'value' in prevItemVal) {
        newLineItems[index] = { 
          ...newLineItems[index], 
          [key]: { ...prevItemVal, value: value } 
        };
      } else {
        newLineItems[index] = { ...newLineItems[index], [key]: value };
      }
      
      return { ...prev, line_items: newLineItems };
    });
  };

  const addLineItem = () => {
    setData((prev: any) => {
      const newLineItems = [...(prev.line_items || []), { description: "", quantity: "", amount: "" }];
      return { ...prev, line_items: newLineItems };
    });
  };

  const removeLineItem = (index: number) => {
    setData((prev: any) => {
      const newLineItems = prev.line_items.filter((_: any, i: number) => i !== index);
      return { ...prev, line_items: newLineItems };
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus("saving");
    try {
      await axios.put(`http://localhost:8000/api/v1/documents/${documentId}/summary`, {
        summary: JSON.stringify(data)
      });
      setSaveStatus("success");
      onSaveSuccess();
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (error) {
      console.error(error);
      setSaveStatus("error");
    } finally {
      setIsSaving(false);
    }
  };

  if (Object.keys(data).length === 0) {
    return <div className="text-slate-400 p-8 text-center">No structured data found.</div>;
  }

  const getDisplayValue = (val: any) => {
    if (val && typeof val === 'object' && 'value' in val) {
      return val.value || "";
    }
    return val || "";
  };

  // Determine which field contains the 2D table data (usually 'table')
  const tableKey = Object.keys(data).find(key => {
    const val = getDisplayValue(data[key]);
    return Array.isArray(val) && val.length > 0 && Array.isArray(val[0]);
  });
  
  const topLevelFields = Object.keys(data).filter(key => key !== tableKey && key !== "line_items");
  
  const tableData: any[][] = tableKey ? getDisplayValue(data[tableKey]) : [];

  const handleTableCellChange = (rowIndex: number, colIndex: number, value: string) => {
    if (!tableKey) return;
    setData((prev: any) => {
      const prevField = prev[tableKey];
      const isObject = prevField && typeof prevField === 'object' && 'value' in prevField;
      const currentTable = isObject ? prevField.value : prevField;
      
      const newTable = currentTable.map((row: any[], rIdx: number) => {
        if (rIdx === rowIndex) {
          const newRow = [...row];
          newRow[colIndex] = value;
          return newRow;
        }
        return row;
      });
      
      if (isObject) {
        return { ...prev, [tableKey]: { ...prevField, value: newTable } };
      }
      return { ...prev, [tableKey]: newTable };
    });
  };

  const addTableRow = () => {
    if (!tableKey || tableData.length === 0) return;
    setData((prev: any) => {
      const prevField = prev[tableKey];
      const isObject = prevField && typeof prevField === 'object' && 'value' in prevField;
      const currentTable = isObject ? prevField.value : prevField;
      
      const emptyRow = new Array(currentTable[0].length).fill("");
      const newTable = [...currentTable, emptyRow];
      
      if (isObject) {
        return { ...prev, [tableKey]: { ...prevField, value: newTable } };
      }
      return { ...prev, [tableKey]: newTable };
    });
  };

  const removeTableRow = (rowIndex: number) => {
    if (!tableKey) return;
    setData((prev: any) => {
      const prevField = prev[tableKey];
      const isObject = prevField && typeof prevField === 'object' && 'value' in prevField;
      const currentTable = isObject ? prevField.value : prevField;
      
      const newTable = currentTable.filter((_: any, idx: number) => idx !== rowIndex);
      
      if (isObject) {
        return { ...prev, [tableKey]: { ...prevField, value: newTable } };
      }
      return { ...prev, [tableKey]: newTable };
    });
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      
      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        
        {/* Top Level Fields Section */}
        <div>
          <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
            <span className="material-symbols-outlined text-[18px] text-indigo-500">receipt</span> 
            Invoice Details
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topLevelFields.map((key) => (
              <div key={key} className="space-y-1">
                <label className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-wider">{key.replace(/_/g, " ")}</label>
                <input 
                  type="text" 
                  value={getDisplayValue(data[key])}
                  onChange={(e) => handleFieldChange(key, e.target.value)}
                  className="w-full text-[13px] bg-slate-50 border border-slate-200 rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-sans font-medium"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Table / Line Items Section */}
        {tableData.length > 0 && (
          <div>
            <div className="flex justify-between items-center mb-4 border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-indigo-500">table_rows</span> 
                {tableKey ? tableKey.toUpperCase() : "LINE ITEMS"}
              </h3>
              <button onClick={addTableRow} className="text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded transition-colors flex items-center gap-1 text-[11px] font-bold">
                <Plus className="w-3 h-3" /> Add Row
              </button>
            </div>
            
            <div className="border border-slate-200 rounded-lg overflow-x-auto">
              <table className="w-full text-left text-[13px] min-w-max">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2 font-mono text-[10px] text-slate-500 uppercase w-10">#</th>
                    {tableData[0].map((header, idx) => (
                      <th key={idx} className="px-3 py-2 font-mono text-[10px] text-slate-500 uppercase">
                        {header}
                      </th>
                    ))}
                    <th className="px-3 py-2 font-mono text-[10px] text-slate-500 uppercase w-12"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tableData.slice(1).map((row: any[], rIdx: number) => (
                    <tr key={rIdx} className="group hover:bg-slate-50/50">
                      <td className="px-3 py-2 text-slate-400 font-mono text-[11px]">{rIdx + 1}</td>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-2">
                          <input 
                            type="text" 
                            value={cell || ""}
                            onChange={(e) => handleTableCellChange(rIdx + 1, cIdx, e.target.value)}
                            className="w-full bg-transparent border-none rounded px-2 py-1 text-[13px] outline-none focus:bg-white focus:ring-1 focus:ring-indigo-200 font-medium"
                          />
                        </td>
                      ))}
                      <td className="px-3 py-2 text-right">
                        <button onClick={() => removeTableRow(rIdx + 1)} className="text-slate-300 hover:text-rose-500 hover:bg-rose-50 p-1.5 rounded transition-all opacity-0 group-hover:opacity-100">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Floating Save Bar */}
      <div className="border-t border-slate-200 bg-slate-50 px-6 py-4 flex items-center justify-between shrink-0 sticky bottom-0">
        <span className="text-xs text-slate-500 font-medium">
          Make corrections to the extracted data above before exporting.
        </span>
        <button 
          onClick={handleSave} 
          disabled={isSaving || saveStatus === "success"}
          className={`flex items-center gap-2 px-5 py-2 rounded shadow-sm text-sm font-bold transition-colors ${
            saveStatus === "success" 
              ? "bg-emerald-500 text-white" 
              : saveStatus === "error"
              ? "bg-rose-500 text-white"
              : "bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-70"
          }`}
        >
          {saveStatus === "saving" && <span className="material-symbols-outlined animate-spin text-[18px]">sync</span>}
          {saveStatus === "success" && <Check className="w-4 h-4" />}
          {saveStatus === "error" && <span className="material-symbols-outlined text-[18px]">error</span>}
          {saveStatus === "idle" && <Save className="w-4 h-4" />}
          
          {saveStatus === "saving" ? "Saving..." : saveStatus === "success" ? "Saved Successfully!" : "Save Changes"}
        </button>
      </div>

    </div>
  );
}
