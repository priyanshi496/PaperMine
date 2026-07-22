"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, File, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import axios from "axios";
import { useRouter } from "next/navigation";

export default function FileUpload() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type !== "application/pdf") {
        setStatus("error");
        setMessage("Only PDF files are allowed.");
        return;
      }
      setFile(selectedFile);
      setStatus("idle");
      setProgress(0);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type !== "application/pdf") {
        setStatus("error");
        setMessage("Only PDF files are allowed.");
        return;
      }
      setFile(droppedFile);
      setStatus("idle");
      setProgress(0);
    }
  };

  const uploadFile = async () => {
    if (!file) return;

    setUploading(true);
    setStatus("idle");
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/api/v1/documents/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(percentCompleted);
          }
        },
      });

      setStatus("success");
      setMessage(`Successfully uploaded ${response.data.filename}`);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      
      // Redirect to document page
      router.push(`/document/${response.data.id}`);
    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setMessage(err.response?.data?.detail || "An error occurred during upload.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white/50 backdrop-blur-xl rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100/50">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-gray-800 tracking-tight">Upload Document</h2>
        <p className="text-sm text-gray-500 mt-2">Upload your PDF for parsing and analysis</p>
      </div>

      <div
        className={`relative border-2 border-dashed rounded-xl p-10 transition-all duration-200 ease-in-out flex flex-col items-center justify-center text-center cursor-pointer group ${
          file ? "border-blue-400 bg-blue-50/50" : "border-gray-200 hover:border-blue-400 hover:bg-gray-50/50"
        }`}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={uploading}
        />
        
        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="p-4 rounded-full bg-blue-100 text-blue-600">
              <File className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">{file.name}</p>
              <p className="text-xs text-gray-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="p-4 rounded-full bg-gray-100 text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Click to upload or drag and drop</p>
              <p className="text-xs text-gray-400 mt-1">PDF files only (max 10MB)</p>
            </div>
          </div>
        )}
      </div>

      {uploading && (
        <div className="mt-6 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Uploading...
            </span>
            <span className="text-gray-500">{progress}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {status === "success" && (
        <div className="mt-6 p-4 bg-green-50 rounded-lg flex items-start gap-3 border border-green-100">
          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-green-700">{message}</p>
        </div>
      )}

      {status === "error" && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg flex items-start gap-3 border border-red-100">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{message}</p>
        </div>
      )}

      <button
        onClick={uploadFile}
        disabled={!file || uploading}
        className="mt-6 w-full py-3 px-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium rounded-xl transition-colors duration-200 focus:ring-4 focus:ring-gray-100 outline-none"
      >
        {uploading ? "Processing..." : "Upload Document"}
      </button>
    </div>
  );
}
