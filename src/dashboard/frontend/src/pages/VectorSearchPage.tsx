import React, { useState } from "react";
import { Search, Sparkles, RefreshCw, Filter, ArrowUpRight, Database, Code2 } from "lucide-react";

interface SearchResult {
  id: string;
  record_type: string;
  title: string;
  similarity_score: number;
  payload: Record<string, any>;
}

export const VectorSearchPage: React.FC = () => {
  const [query, setQuery] = useState("autonomous AI data pipeline");
  const [filterType, setFilterType] = useState("all");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${filterType}&limit=12`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch (err) {
      console.error("Vector search failed", err);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    setReindexStatus(null);
    try {
      const res = await fetch("/api/search/reindex", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setReindexStatus(`Indexed ${data.indexedCount} entities into LanceDB (${data.vectorDimension}D)`);
        handleSearch();
      }
    } catch (err) {
      setReindexStatus("Reindexing failed");
    } finally {
      setReindexing(false);
    }
  };

  React.useEffect(() => {
    handleSearch();
  }, [filterType]);

  const getTypeBadgeColor = (type: string) => {
    switch (type) {
      case "startup": return "bg-[#7ee787]/15 text-[#7ee787] border-[#7ee787]/30";
      case "product": return "bg-[#d2a8ff]/15 text-[#d2a8ff] border-[#d2a8ff]/30";
      case "research_paper": return "bg-[#79c0ff]/15 text-[#79c0ff] border-[#79c0ff]/30";
      case "job": return "bg-[#e3b341]/15 text-[#e3b341] border-[#e3b341]/30";
      case "news": return "bg-[#f0883e]/15 text-[#f0883e] border-[#f0883e]/30";
      default: return "bg-[#8b8f94]/15 text-[#8b8f94] border-[#8b8f94]/30";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1f2124] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#7ee787]" />
            <h1 className="text-xl font-bold font-mono tracking-tight text-[#e6e6e6]">
              HYBRID VECTOR SEARCH & SEMANTIC INDEX
            </h1>
          </div>
          <p className="text-xs text-[#8b8f94] font-mono mt-1">
            LanceDB columnar vector embeddings (128D) with real-time cosine similarity & hybrid BM25 ranking
          </p>
        </div>

        <button
          onClick={handleReindex}
          disabled={reindexing}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#14171d] border border-[#272a30] hover:border-[#7ee787]/50 text-xs font-mono text-[#e6e6e6] transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-[#7ee787] ${reindexing ? "animate-spin" : ""}`} />
          {reindexing ? "Reindexing LanceDB..." : "Reindex LanceDB Store"}
        </button>
      </div>

      {reindexStatus && (
        <div className="px-4 py-2.5 rounded-lg bg-[#7ee787]/10 border border-[#7ee787]/30 text-xs font-mono text-[#7ee787]">
          ✓ {reindexStatus}
        </div>
      )}

      {/* Main Search Bar */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="relative flex items-center">
          <Search className="absolute left-4 w-5 h-5 text-[#8b8f94]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across all ingested entities by context, domain, or technology..."
            className="w-full pl-12 pr-28 py-3.5 bg-[#0f1115] border border-[#272a30] rounded-xl text-sm font-mono text-[#e6e6e6] focus:outline-none focus:border-[#7ee787] placeholder-[#5b5f66] shadow-lg transition-colors"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 px-4 py-2 bg-[#7ee787] hover:bg-[#68d472] text-[#0a0b0d] font-mono font-bold text-xs rounded-lg transition-colors"
          >
            {loading ? "Searching..." : "Search Vectors"}
          </button>
        </div>

        {/* Entity Category Filter Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-[#8b8f94] flex items-center gap-1.5 mr-2">
            <Filter className="w-3.5 h-3.5 text-[#4a4d52]" /> Filter Type:
          </span>
          {[
            { id: "all", label: "All Types" },
            { id: "startup", label: "Startups" },
            { id: "product", label: "Products" },
            { id: "research_paper", label: "Papers" },
            { id: "job", label: "Jobs" },
            { id: "news", label: "News" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilterType(tab.id)}
              className={`px-3 py-1.5 rounded-md font-mono text-xs transition-colors ${
                filterType === tab.id
                  ? "bg-[#1f242d] text-[#7ee787] border border-[#7ee787]/40 font-semibold"
                  : "bg-[#0f1115] text-[#8b8f94] border border-[#1f2124] hover:text-[#e6e6e6]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </form>

      {/* Results Count Summary */}
      <div className="flex items-center justify-between text-xs font-mono text-[#8b8f94]">
        <span>Found {results.length} semantic similarity match{results.length !== 1 ? "es" : ""}</span>
        <span>Storage: LanceDB Columnar Index</span>
      </div>

      {/* Results Grid */}
      {results.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-[#272a30] rounded-xl bg-[#0f1115]">
          <Database className="w-8 h-8 text-[#4a4d52] mx-auto mb-3" />
          <p className="text-sm font-mono text-[#8b8f94]">No semantic matches found for "{query}".</p>
          <p className="text-xs font-mono text-[#4a4d52] mt-1">Try searching for keywords like "AI", "pipeline", "LLM", "audio", or "agent".</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((res) => {
            const matchPct = Math.round(res.similarity_score * 100);
            return (
              <div
                key={res.id}
                className="group relative bg-[#0f1115] border border-[#272a30] hover:border-[#7ee787]/50 rounded-xl p-5 flex flex-col justify-between transition-all hover:shadow-xl"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border uppercase ${getTypeBadgeColor(res.record_type)}`}>
                      {res.record_type}
                    </span>
                    <span className="font-mono text-xs font-bold text-[#7ee787] bg-[#7ee787]/10 px-2 py-0.5 rounded border border-[#7ee787]/20">
                      {matchPct}% Match
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-[#e6e6e6] font-mono leading-snug group-hover:text-[#7ee787] transition-colors">
                    {res.title}
                  </h3>

                  <p className="text-xs text-[#8b8f94] line-clamp-3 mt-2 font-mono leading-relaxed">
                    {res.payload.description || res.payload.abstract || res.payload.tagline || res.payload.summary || "No description provided."}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-[#1f2124] flex items-center justify-between">
                  <span className="text-[11px] font-mono text-[#4a4d52]">
                    ID: {res.id.slice(0, 18)}
                  </span>
                  <button
                    onClick={() => setSelectedResult(res)}
                    className="inline-flex items-center gap-1 text-xs font-mono text-[#7ee787] hover:underline"
                  >
                    <Code2 className="w-3.5 h-3.5" /> Payload
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* JSON Payload Modal */}
      {selectedResult && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          onClick={() => setSelectedResult(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl bg-[#0f1115] border border-[#272a30] rounded-xl p-6 shadow-2xl max-h-[80vh] flex flex-col"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[#272a30]">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono border uppercase ${getTypeBadgeColor(selectedResult.record_type)}`}>
                  {selectedResult.record_type}
                </span>
                <h2 className="text-sm font-bold font-mono text-[#e6e6e6]">{selectedResult.title}</h2>
              </div>
              <button
                onClick={() => setSelectedResult(null)}
                className="text-xs font-mono text-[#8b8f94] hover:text-[#e6e6e6]"
              >
                ✕ Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 p-4 rounded-lg bg-[#0a0b0d] border border-[#1f2124]">
              <pre className="text-xs font-mono text-[#7ee787] whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(selectedResult.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
