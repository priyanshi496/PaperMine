"use client";

import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";

export default function AssistantPage() {
  const { authState } = useAuth();
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<any[]>([
    { role: "assistant", content: "Good morning. I've finished indexing your financial data. How can I help you navigate your data today?", sources: [] }
  ]);
  const [loading, setLoading] = useState(false);
  
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSend = async () => {
    if (!query.trim()) return;
    
    const userMessage = { role: "user", content: query, sources: [] };
    const currentQuery = query;
    setQuery("");
    
    const newHistory = [...chatHistory, userMessage];
    setChatHistory(newHistory);
    setLoading(true);
    
    try {
      // Send chat history without the sources array attached to each message (API expects just role/content)
      const cleanHistory = newHistory.map(msg => ({ role: msg.role, content: msg.content }));
      
      const res = await axios.post("http://localhost:8000/api/v1/assistant/chat", {
        query: currentQuery,
        chat_history: cleanHistory
      });
      
      setChatHistory([
        ...newHistory,
        { role: "assistant", content: res.data.answer, sources: res.data.sources || [] }
      ]);
    } catch (e) {
      setChatHistory([
        ...newHistory,
        { role: "assistant", content: "Error connecting to the intelligence engine.", sources: [] }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!authState.user) return null;

  return (
    <div className="pt-16 min-h-screen flex flex-col bg-slate-50 relative">
      <div className="flex-1 max-w-4xl w-full mx-auto p-4 flex flex-col h-[calc(100vh-64px)]">
        
        {/* Header */}
        <div className="mb-4 text-center">
            <h1 className="text-2xl font-bold text-slate-800">Financial Intelligence Assistant</h1>
            <p className="text-slate-500 text-sm">Ask anything about your cash flow, taxes, or vendor contracts.</p>
        </div>
        
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto rounded-xl bg-white border border-slate-200 shadow-sm p-4 space-y-6 mb-4 relative">
          {chatHistory.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0 ${msg.role === "user" ? "bg-blue-600" : "bg-slate-800"}`}>
                <span className="material-symbols-outlined">{msg.role === "user" ? "person" : "smart_toy"}</span>
              </div>
              <div className={`max-w-[80%] ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-800"} p-4 rounded-2xl ${msg.role === "user" ? "rounded-tr-sm" : "rounded-tl-sm"}`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-300/30 flex flex-col gap-2">
                    <span className="text-xs font-bold opacity-70 uppercase tracking-widest">Sources</span>
                    <div className="flex flex-wrap gap-2">
                        {msg.sources.map((src: any, sIdx: number) => (
                            <div key={sIdx} className="bg-white/50 border border-slate-300/50 rounded flex items-center gap-2 px-2 py-1">
                                <span className="material-symbols-outlined text-[14px]">description</span>
                                <span className="text-xs font-mono">{src.type} {src.document_id ? `#${src.document_id}` : ''}</span>
                                {src.relevance && <span className="text-[10px] bg-slate-200 px-1 rounded text-slate-600">{src.relevance} dist</span>}
                            </div>
                        ))}
                    </div>
                  </div>
                )}
                
                {/* Workflow Actions for Assistant messages containing specific triggers (mock implementation) */}
                {msg.role === "assistant" && msg.content.includes("high-risk") && (
                    <div className="mt-3 flex gap-2">
                        <button className="px-3 py-1 bg-red-100 text-red-700 text-xs font-bold rounded shadow-sm hover:bg-red-200">Review Invoices</button>
                    </div>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0 bg-slate-800">
                <span className="material-symbols-outlined animate-pulse">smart_toy</span>
              </div>
              <div className="max-w-[80%] bg-slate-100 text-slate-800 p-4 rounded-2xl rounded-tl-sm flex items-center gap-2">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: "150ms"}}></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: "300ms"}}></span>
              </div>
            </div>
          )}
          
          <div ref={endOfMessagesRef} />
        </div>
        
        {/* Input Area */}
        <div className="flex items-center gap-3 bg-white border border-slate-200 p-2 rounded-xl shadow-sm">
          <input 
            type="text" 
            className="flex-1 bg-transparent border-none focus:ring-0 text-slate-800 p-2 text-sm outline-none"
            placeholder="Ask a question about your data..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            disabled={loading}
          />
          <button 
            onClick={handleSend}
            disabled={loading || !query.trim()}
            className="w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center justify-center disabled:opacity-50 transition-colors"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
        
      </div>
    </div>
  );
}
