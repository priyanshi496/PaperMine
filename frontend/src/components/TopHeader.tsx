"use client";

import { useAuth } from "@/context/AuthContext";
import { LogOut, Search, Plus, Upload, Bot, FileText, Bell, History, Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function TopHeader() {
  const router = useRouter();
  const { authState, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  
  // ⌘K Shortcut Listener
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  if (!authState.user) return null;

  return (
    <>
      <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        
        {/* Global Search Button */}
        <div className="flex flex-1 items-center gap-4">
          <Button 
            variant="outline" 
            className="relative h-9 w-full justify-start rounded-[0.5rem] bg-muted/50 text-sm font-normal text-muted-foreground shadow-none sm:pr-12 md:w-80 lg:w-96"
            onClick={() => setOpen(true)}
          >
            <Search className="mr-2 h-4 w-4" />
            <span className="hidden lg:inline-flex">Search invoices, vendors, or AI...</span>
            <span className="inline-flex lg:hidden">Search...</span>
            <kbd className="pointer-events-none absolute right-[0.3rem] top-[0.3rem] hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          
          {/* Quick Actions */}
          <DropdownMenu>
            <DropdownMenuTrigger className={cn(buttonVariants({ variant: "default", size: "sm" }), "h-9 gap-1 mr-2 rounded-full cursor-pointer")}>
              <Plus className="h-4 w-4" />
              <span className="hidden md:inline">Quick Action</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="cursor-pointer" onClick={() => router.push('/documents')}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Invoice
              </DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer">
                <Bot className="mr-2 h-4 w-4" />
                Ask AI Assistant
              </DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer">
                <FileText className="mr-2 h-4 w-4" />
                Generate Report
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme Toggle */}
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-muted-foreground"
          >
            <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="text-muted-foreground relative">
            <Bell className="h-5 w-5" />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500"></span>
          </Button>
          
        </div>
      </header>

      {/* Command Palette Modal */}
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Suggestions">
            <CommandItem>
              <Bot className="mr-2 h-4 w-4" />
              <span>Ask AI Copilot</span>
              <CommandShortcut>⌘A</CommandShortcut>
            </CommandItem>
            <CommandItem>
              <FileText className="mr-2 h-4 w-4" />
              <span>View recent invoices</span>
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Vendors">
            <CommandItem>
              <span>Dell Technologies</span>
            </CommandItem>
            <CommandItem>
              <span>Metro Wholesale</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
