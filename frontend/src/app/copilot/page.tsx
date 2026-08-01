"use client";

import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useSearchParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Send, FileText, Search, BarChart3, ShieldAlert, Check, Copy, LineChart, TrendingUp, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { motion, AnimatePresence } from "framer-motion";

import { usePageContext } from "@/context/PageContext";

export default function CopilotPage() {
  const { authState, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [loadingPhase, setLoadingPhase] = useState(0);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const { setPageContext, pageContext } = usePageContext();
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

  useEffect(() => {
    let interval: any;
    if (loading) {
      setLoadingPhase(0);
      interval = setInterval(() => {
        setLoadingPhase((p) => (p < 3 ? p + 1 : p));
      }, 800);
    } else {
      setLoadingPhase(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSend = async (forcedQuery?: string) => {
    const textToSend = forcedQuery || query;
    if (!textToSend.trim()) return;

    const userMessage = { role: "user", content: textToSend, sources: [] };
    setChatHistory((prev) => [
      ...prev,
      userMessage,
      { role: "assistant", content: "", sources: [] }
    ]);
    
    // The index of the AI message we just pushed
    const aiMessageIndex = chatHistory.length + 1;
    
    setQuery("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/assistant/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authState.token}`
        },
        body: JSON.stringify({
          query: textToSend,
          chat_history: chatHistory.map((m) => ({ role: m.role, content: m.content })),
          frontend_context: pageContext
        })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.substring(6).trim();
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              setChatHistory((prev) => {
                const newHistory = [...prev];
                const msg = { ...newHistory[aiMessageIndex] };
                
                if (data.sources) {
                  msg.sources = data.sources;
                }
                if (data.chunk) {
                  msg.content += data.chunk;
                }
                
                newHistory[aiMessageIndex] = msg;
                return newHistory;
              });
            } catch (e) {
              console.error("Error parsing SSE data", dataStr, e);
            }
          }
        }
      }
    } catch (e: any) {
      setChatHistory((prev) => {
        const newHistory = [...prev];
        if (newHistory[aiMessageIndex]) {
           newHistory[aiMessageIndex].content = "Sorry, I encountered an error. Please try again.";
        }
        return newHistory;
      });
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

  const role = authState.user?.role || "vendor";

  const PROMPTS = {
    vendor: [
      { icon: <BarChart3 className="w-5 h-5 text-blue-500" />, title: "Show my revenue this month." },
      { icon: <ShieldAlert className="w-5 h-5 text-red-500" />, title: "Which of my invoices are pending?" },
      { icon: <FileText className="w-5 h-5 text-emerald-500" />, title: "Summarize my latest invoice." },
    ],
    finance_team: [
      { icon: <Search className="w-5 h-5 text-purple-500" />, title: "Show pending approvals." },
      { icon: <ShieldAlert className="w-5 h-5 text-red-500" />, title: "Are there any GST mismatches?" },
      { icon: <FileText className="w-5 h-5 text-amber-500" />, title: "Show all high-risk invoices." },
    ],
    cfo: [
      { icon: <LineChart className="w-5 h-5 text-indigo-500" />, title: "Compare our top vendors." },
      { icon: <TrendingUp className="w-5 h-5 text-emerald-500" />, title: "Generate a monthly spend report." },
      { icon: <BarChart3 className="w-5 h-5 text-blue-500" />, title: "Why did IT spending increase?" },
    ]
  };

  const suggestedPrompts = PROMPTS[role as keyof typeof PROMPTS] || PROMPTS.vendor;

  const loadingMessages = [
    "Thinking...",
    "Querying Financial Database...",
    "Searching Company Knowledge...",
    "Combining Results..."
  ];

  return (
    <>
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
                      <div className="group relative">
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-tables:border-collapse prose-th:border prose-th:border-border prose-th:bg-muted/50 prose-th:p-2 prose-td:border prose-td:border-border prose-td:p-2">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                          
                            {msg.sources && msg.sources.length > 0 && (
                              <div className="mt-4 pt-4 border-t border-border/50 flex flex-wrap gap-2">
                                {msg.sources.map((src: any, i: number) => (
                                  <Badge 
                                    key={i} 
                                    variant="outline" 
                                    className="text-[10px] bg-background cursor-pointer hover:bg-muted"
                                    onClick={() => setSelectedSource(src)}
                                  >
                                    {src.type === "SQL Database" ? <BarChart3 className="w-3 h-3 mr-1 text-blue-500" /> : <FileText className="w-3 h-3 mr-1 text-emerald-500" />}
                                    {src.type === "Business Document" ? src.filename : (src.type === "SQL Database" ? "SQL Database" : `Invoice Document ${src.document_id}`)}
                                  </Badge>
                                ))}
                              </div>
                            )}

                            {idx === chatHistory.length - 1 && !loading && msg.content && (
                              <div className="mt-4 pt-4 border-t border-border/50 flex flex-wrap gap-2">
                                <p className="w-full text-[10px] uppercase tracking-wider font-bold text-muted-foreground mb-1">Suggested Follow-ups</p>
                                {["Explain the root cause", "Show supporting documents", "Compare with last month"].map((suggestion) => (
                                  <Badge
                                    key={suggestion}
                                    variant="secondary"
                                    className="text-[11px] cursor-pointer hover:bg-primary/20 text-primary bg-primary/10"
                                    onClick={() => handleSend(suggestion)}
                                  >
                                    {suggestion}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>

                        {/* Copy Button */}
                        {msg.content && (
                          <div className="absolute -bottom-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger
                                  className="inline-flex shrink-0 items-center justify-center border bg-background hover:bg-accent hover:text-accent-foreground h-7 w-7 rounded-full shadow-sm"
                                  onClick={() => handleCopy(msg.content, idx)}
                                >
                                  {copiedIndex === idx ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3 text-muted-foreground" />}
                                </TooltipTrigger>
                                <TooltipContent side="top">
                                  <p className="text-[10px]">{copiedIndex === idx ? "Copied" : "Copy to clipboard"}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
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
                <div className="bg-muted/30 border border-border/50 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-3">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-[13px] font-medium text-muted-foreground animate-pulse">
                    {loadingMessages[loadingPhase]}
                  </span>
                </div>
              </motion.div>
            )}
            <div ref={endOfMessagesRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background border-t">
        <div className="flex items-center gap-2 max-w-3xl mx-auto w-full">
          <form 
            className="relative flex items-center flex-1 bg-muted/30 border rounded-full shadow-sm focus-within:ring-1 focus-within:ring-primary/50 transition-all p-1"
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
              className="rounded-full h-10 w-10 bg-primary/90 hover:bg-primary transition-all mr-1"
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>

          {chatHistory.length > 0 && (
            <Button 
              variant="outline" 
              size="icon" 
              onClick={() => setChatHistory([])}
              title="Clear chat history"
              className="rounded-full shrink-0 h-11 w-11 border-dashed text-muted-foreground hover:text-red-500 hover:border-red-500 hover:bg-red-500/10 transition-colors"
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          )}
        </div>
        <p className="text-center text-[11px] text-muted-foreground mt-3 font-medium">
          PaperMine AI can make mistakes. Check important numbers.
        </p>
      </div>

    </div>

      <Sheet open={!!selectedSource} onOpenChange={(open) => !open && setSelectedSource(null)}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              {selectedSource?.filename || "Source Document"}
            </SheetTitle>
            <SheetDescription>
              {selectedSource?.type || "Document Chunk"}
            </SheetDescription>
          </SheetHeader>
          
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {selectedSource?.text || ""}
            </ReactMarkdown>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
