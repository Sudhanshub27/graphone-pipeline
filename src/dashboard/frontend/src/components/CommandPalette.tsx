import React, { useEffect, useState } from "react";
import { Command } from "cmdk";
import { Search, LayoutDashboard, Database, GitMerge, Terminal, Sparkles, Loader2 } from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectNav: (route: string, entityType?: string) => void;
}

interface SearchResult {
  id: string;
  record_type: string;
  title: string;
  similarity_score: number;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  open,
  onOpenChange,
  onSelectNav,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

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

  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}&limit=6`);
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.results || []);
        }
      } catch (err) {
        console.error("Vector search failed", err);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/75 backdrop-blur-[4px]"
      onClick={() => onOpenChange(false)}
    >
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-[640px] px-4">
        <Command label="Vector Command Palette" className="shadow-2xl bg-[#0f1115] border border-[#272a30] rounded-xl overflow-hidden">
          <div className="flex items-center px-4 py-3 border-b border-[#272a30] bg-[#14171d]">
            <Search className="w-4 h-4 text-[#8b8f94] mr-3" />
            <Command.Input
              value={searchQuery}
              onValueChange={setSearchQuery}
              placeholder="Search vector embeddings or commands (e.g., AI pipelines, Whisper)..."
              className="w-full bg-transparent text-sm text-[#e6e6e6] focus:outline-none placeholder-[#5b5f66]"
            />
            {isSearching && <Loader2 className="w-4 h-4 text-[#7ee787] animate-spin ml-2" />}
          </div>

          <Command.List className="max-h-[380px] overflow-y-auto p-2">
            <Command.Empty className="p-4 text-xs font-mono text-[#8b8f94] text-center">
              No vector similarity matches found.
            </Command.Empty>

            {searchResults.length > 0 && (
              <Command.Group heading="Vector Semantic Matches (LanceDB)">
                {searchResults.map((res) => (
                  <Command.Item
                    key={res.id}
                    onSelect={() => {
                      onSelectNav("browser", res.record_type);
                      onOpenChange(false);
                    }}
                    className="flex items-center justify-between p-2.5 rounded-md hover:bg-[#1f232b] cursor-pointer text-xs transition-colors"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <Sparkles className="w-3.5 h-3.5 text-[#7ee787] shrink-0" />
                      <span className="text-[#e6e6e6] font-medium truncate">{res.title}</span>
                      <span className="px-1.5 py-0.5 rounded bg-[#1b2028] text-[10px] text-[#8b8f94] font-mono uppercase">
                        {res.record_type}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-[#7ee787] bg-[#7ee787]/10 px-2 py-0.5 rounded border border-[#7ee787]/20">
                      {Math.round(res.similarity_score * 100)}% match
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            <Command.Group heading="Quick Navigation">
              <Command.Item
                onSelect={() => {
                  onSelectNav("overview");
                  onOpenChange(false);
                }}
                className="flex items-center gap-3 p-2 rounded hover:bg-[#1a1d24] cursor-pointer text-xs"
              >
                <LayoutDashboard className="w-4 h-4 text-[#7ee787]" />
                <span className="flex-1 text-[#d0d4dc]">Overview Dashboard</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("graph");
                  onOpenChange(false);
                }}
                className="flex items-center gap-3 p-2 rounded hover:bg-[#1a1d24] cursor-pointer text-xs"
              >
                <GitMerge className="w-4 h-4 text-[#9d7ee8]" />
                <span className="flex-1 text-[#d0d4dc]">Knowledge Graph Explorer</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("browser");
                  onOpenChange(false);
                }}
                className="flex items-center gap-3 p-2 rounded hover:bg-[#1a1d24] cursor-pointer text-xs"
              >
                <Database className="w-4 h-4 text-[#e6e6e6]" />
                <span className="flex-1 text-[#d0d4dc]">Data Browser</span>
              </Command.Item>

              <Command.Item
                onSelect={() => {
                  onSelectNav("logs");
                  onOpenChange(false);
                }}
                className="flex items-center gap-3 p-2 rounded hover:bg-[#1a1d24] cursor-pointer text-xs"
              >
                <Terminal className="w-4 h-4 text-[#6e9fe0]" />
                <span className="flex-1 text-[#d0d4dc]">Pipeline Logs</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
};
