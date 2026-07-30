"use client";

import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useSearchParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Send, FileText, Search, BarChart3, ShieldAlert } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { motion, AnimatePresence } from "framer-motion";

export default function CopilotPage() {
  const { authState, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  const storageKey = `papermine_copilot_${(authState.user as any)?.id ?? "guest"}`;

  useEffect(() => {
    if (!authState.user) return;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setChatHistory(parsed);
          setHydrated(true);
          return;
        }
      }
    } catch (_) {}
    setHydrated(true);
  }, [authState.user]);

  useEffect(() => {
    if (!hydrated || !authState.user) return;
    localStorage.setItem(storageKey, JSON.stringify(chatHistory));
  }, [chatHistory, hydrated]);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, loading]);

  const handleSend = async (forcedQuery?: string) => {
    const textToSend = forcedQuery || query;
    if (!textToSend.trim()) return;

    const userMessage = { role: "user", content: textToSend, sources: [] };
    setChatHistory((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      const res = await axios.post(
        "http://localhost:8000/api/v1/assistant/chat",
        {
          query: textToSend,
          chat_history: chatHistory.map((m) => ({ role: m.role, content: m.content }))
        },
        {
          headers: {
            Authorization: `Bearer ${authState.token}`
          }
        }
      );

      const aiMessage = {
        role: "assistant",
        content: res.data.answer,
        sources: res.data.sources || [],
      };
      setChatHistory((prev) => [...prev, aiMessage]);
    } catch (e: any) {
      const errorMsg = {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        sources: [],
      };
      setChatHistory((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hydrated && authState.user && searchParams?.get("q")) {
      const q = searchParams.get("q");
      if (q) {
        handleSend(q);
        router.replace("/copilot");
      }
    }
  }, [hydrated, authState.user, searchParams, router]);

  if (authLoading || !hydrated) return null;

  const suggestedPrompts = [
    { icon: <BarChart3 className="w-5 h-5 text-blue-500" />, title: "Which vendor cost us the most this month?" },
    { icon: <ShieldAlert className="w-5 h-5 text-red-500" />, title: "Show me all high-risk unverified invoices." },
    { icon: <FileText className="w-5 h-5 text-emerald-500" />, title: "Summarize the latest invoice from Dell." },
    { icon: <Search className="w-5 h-5 text-purple-500" />, title: "What products do we buy most from Metro?" },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-4xl mx-auto w-full">
      
      {/* Scrollable Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        
        {chatHistory.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center animate-in fade-in zoom-in duration-500">
            <div className="h-16 w-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-primary/20">
              <Bot className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mb-2 text-center">
              Good Morning, {authState.user?.email.split('@')[0]}
            </h1>
            <p className="text-muted-foreground mb-12 text-center max-w-md">
              I am your PaperMine AI Copilot. Ask me anything about your invoices, vendors, or financial risks.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
              {suggestedPrompts.map((prompt, idx) => (
                <Card 
                  key={idx} 
                  className="cursor-pointer hover:bg-muted/50 hover:border-primary/50 transition-all active:scale-[0.98]"
                  onClick={() => handleSend(prompt.title)}
                >
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="p-2 bg-background rounded-lg border shadow-sm">
                      {prompt.icon}
                    </div>
                    <p className="text-sm font-medium">{prompt.title}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-8 pb-10">
            <AnimatePresence initial={false}>
              {chatHistory.map((msg, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}
                  
                  <div className={`max-w-[85%] ${
                    msg.role === "user" 
                      ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm" 
                      : "bg-muted/30 border border-border/50 rounded-2xl rounded-tl-sm px-6 py-5 shadow-sm"
                  }`}>
                    {msg.role === "user" ? (
                      <p className="text-[15px]">{msg.content}</p>
                    ) : (
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-tables:border-collapse prose-th:border prose-th:border-border prose-th:bg-muted/50 prose-th:p-2 prose-td:border prose-td:border-border prose-td:p-2">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                        
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-border/50 flex flex-wrap gap-2">
                            {msg.sources.map((src: any, i: number) => (
                              <Badge key={i} variant="outline" className="text-[10px] bg-background">
                                <FileText className="w-3 h-3 mr-1" />
                                Document {src.document_id}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {loading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-muted/30 border border-border/50 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary/50 animate-bounce"></div>
                  <div className="w-2 h-2 rounded-full bg-primary/50 animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 rounded-full bg-primary/50 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </motion.div>
            )}
            <div ref={endOfMessagesRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background border-t">
        <form 
          className="relative flex items-center w-full max-w-3xl mx-auto bg-muted/30 border rounded-full shadow-sm focus-within:ring-1 focus-within:ring-primary/50 transition-all p-1"
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
        >
          <div className="pl-4 text-muted-foreground">
            <Search className="w-5 h-5" />
          </div>
          <Input 
            className="flex-1 border-none bg-transparent shadow-none focus-visible:ring-0 text-[15px]" 
            placeholder="Ask Copilot about invoices, vendors, or trends..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <Button 
            type="submit" 
            size="icon" 
            disabled={loading || !query.trim()} 
            className="rounded-full h-10 w-10 shrink-0 bg-primary hover:bg-primary/90 text-primary-foreground transition-transform active:scale-95"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
        <p className="text-center text-[11px] text-muted-foreground mt-3 font-medium">
          PaperMine AI can make mistakes. Check important numbers.
        </p>
      </div>

    </div>
  );
}
