import React, { useEffect, useState } from "react";
import { Command } from "cmdk";
import { Search, LayoutDashboard, Database, GitMerge, Terminal, ArrowRight } from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectNav: (route: string, entityType?: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  open,
  onOpenChange,
  onSelectNav,
}) => {
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/70 backdrop-blur-[2px]"
      onClick={() => onOpenChange(false)}
    >
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-[600px] px-4">
        <Command label="Command Palette" className="shadow-2xl">
          <div className="flex items-center px-3 border-b border-[#1f2124]">
            <Search className="w-4 h-4 text-[#8b8f94] mr-2" />
            <Command.Input
              value={searchQuery}
              onValueChange={setSearchQuery}
              placeholder="Type a command or search entities (Cmd+K)..."
            />
          </div>

          <Command.List className="max-h-[320px] overflow-y-auto p-2">
            <Command.Empty className="p-4 text-xs font-mono text-[#8b8f94] text-center">
              No matching commands or entities found.
            </Command.Empty>

            <Command.Group heading="Navigation">
              <Command.Item
                onSelect={() => {
                  onSelectNav("overview");
                  onOpenChange(false);
                }}
              >
                <LayoutDashboard className="w-4 h-4 text-[#7ee787]" />
                <span className="flex-1">Overview Dashboard</span>
                <span className="font-mono text-[11px] text-[#4a4d52]">Jump to Overview</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("browser");
                  onOpenChange(false);
                }}
              >
                <Database className="w-4 h-4 text-[#e6e6e6]" />
                <span className="flex-1">Data Browser</span>
                <span className="font-mono text-[11px] text-[#4a4d52]">Explore records</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("resolution");
                  onOpenChange(false);
                }}
              >
                <GitMerge className="w-4 h-4 text-[#e8b339]" />
                <span className="flex-1">Entity Resolution Log</span>
                <span className="font-mono text-[11px] text-[#4a4d52]">View deduplication</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("logs");
                  onOpenChange(false);
                }}
              >
                <Terminal className="w-4 h-4 text-[#6e9fe0]" />
                <span className="flex-1">Pipeline Logs</span>
                <span className="font-mono text-[11px] text-[#4a4d52]">Live tail logs</span>
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Entity Categories">
              <Command.Item
                onSelect={() => {
                  onSelectNav("browser", "startup");
                  onOpenChange(false);
                }}
              >
                <ArrowRight className="w-3.5 h-3.5 text-[#8b8f94]" />
                <span className="flex-1">Startups</span>
                <span className="font-mono text-[11px] text-[#8b8f94]">Category</span>
              </Command.Item>
              <Command.Item
                onSelect={() => {
                  onSelectNav("browser", "product");
                  onOpenChange(false);
                }}
              >
                <ArrowRight className="w-3.5 h-3.5 text-[#8b8f94]" />
                <span className="flex-1">Products</span>
                <span className="font-mono text-[11px] text-[#8b8f94]">Category</span>
              </Command.Item>
              <Command.Item
                onSelect={() => {
                  onSelectNav("browser", "research_paper");
                  onOpenChange(false);
                }}
              >
                <ArrowRight className="w-3.5 h-3.5 text-[#8b8f94]" />
                <span className="flex-1">Research Papers</span>
                <span className="font-mono text-[11px] text-[#8b8f94]">Category</span>
              </Command.Item>
              <Command.Item
                onSelect={() => {
                  onSelectNav("browser", "job");
                  onOpenChange(false);
                }}
              >
                <ArrowRight className="w-3.5 h-3.5 text-[#8b8f94]" />
                <span className="flex-1">Jobs</span>
                <span className="font-mono text-[11px] text-[#8b8f94]">Category</span>
              </Command.Item>
              <Command.Item
                onSelect={() => {
                  onSelectNav("browser", "news");
                  onOpenChange(false);
                }}
              >
                <ArrowRight className="w-3.5 h-3.5 text-[#8b8f94]" />
                <span className="flex-1">News</span>
                <span className="font-mono text-[11px] text-[#8b8f94]">Category</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
};
