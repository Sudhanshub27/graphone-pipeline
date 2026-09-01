import React, { useEffect, useState } from "react";
import { Filter, CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";

export const EntityResolutionPage: React.FC = () => {
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [data, setData] = useState<any>({ summary: {}, entries: [] });
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch("/api/entity-log")
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load entity log", err);
        setLoading(false);
      });
  }, []);

  const entries = data.entries || [];

  const filteredEntries = React.useMemo(() => {
    if (methodFilter === "all") return entries;
    return entries.filter((e: any) => e.method_used === methodFilter);
  }, [entries, methodFilter]);

  const getMethodBadge = (method: string) => {
    switch (method) {
      case "exact":
        return "text-[#7ee787] border-[#7ee787]/30 bg-[#7ee787]/10";
      case "normalized":
        return "text-[#6e9fe0] border-[#6e9fe0]/30 bg-[#6e9fe0]/10";
      case "fuzzy":
        return "text-[#e8b339] border-[#e8b339]/30 bg-[#e8b339]/10";
      case "unresolved":
      default:
        return "text-[#e5534b] border-[#e5534b]/30 bg-[#e5534b]/10";
    }
  };

  return (
    <div className="space-y-4">
      {/* Header Bar with Method Filter */}
      <div className="flex items-center justify-between p-3 bg-[#131417] border border-[#1f2124] rounded">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[#7ee787]" />
          <h2 className="text-xs font-mono font-bold uppercase text-[#e6e6e6]">
            DEDUPLICATION & RESOLUTION AUDIT LOG
          </h2>
        </div>

        {/* Method Filter Dropdown */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-[#8b8f94]">Filter Method:</span>
          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="h-8 px-2.5 bg-[#0a0b0d] border border-[#1f2124] focus:border-[#7ee787] text-[#e6e6e6] rounded font-mono text-xs outline-none cursor-pointer"
          >
            <option value="all">ALL METHODS ({entries.length})</option>
            <option value="exact">EXACT MATCH</option>
            <option value="normalized">NORMALIZED</option>
            <option value="fuzzy">FUZZY REVIEW</option>
            <option value="unresolved">UNRESOLVED</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="w-full overflow-x-auto border border-[#1f2124] rounded bg-[#131417]">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 z-10 bg-[#0a0b0d] border-b border-[#1f2124] select-none">
            <tr>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">ID</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">Entity Name</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">Type</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">Method Used</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94] text-right">Confidence</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">Status</th>
              <th className="px-4 py-2.5 font-mono text-[11px] uppercase text-[#8b8f94]">Timestamp</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#1f2124]/60 text-xs">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-[#8b8f94] font-mono">
                  Loading resolution log...
                </td>
              </tr>
            ) : filteredEntries.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-[#8b8f94] font-mono">
                  No resolution log entries match filter.
                </td>
              </tr>
            ) : (
              filteredEntries.map((row: any) => {
                const needsReview = row.status === "needs_review";
                return (
                  <tr
                    key={row.id}
                    className={`hover:bg-[#191b1f] transition-colors ${
                      needsReview ? "border-l-2 border-[#e8b339] bg-[#e8b339]/5" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-[#8b8f94]">{row.id}</td>
                    <td className="px-4 py-3 text-[#e6e6e6] font-medium">{row.entity_name}</td>
                    <td className="px-4 py-3 font-mono text-[#8b8f94] uppercase text-[10px]">
                      {row.entity_type}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-mono uppercase font-bold ${getMethodBadge(
                          row.method_used
                        )}`}
                      >
                        {row.method_used}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono tabular-nums text-right text-[#e6e6e6] font-bold">
                      {(row.confidence_score * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px]">
                      {row.status === "merged" && (
                        <span className="inline-flex items-center gap-1 text-[#7ee787]">
                          <CheckCircle2 className="w-3 h-3" /> MERGED
                        </span>
                      )}
                      {row.status === "needs_review" && (
                        <span className="inline-flex items-center gap-1 text-[#e8b339] font-bold">
                          <AlertTriangle className="w-3 h-3" /> NEEDS REVIEW
                        </span>
                      )}
                      {row.status === "kept_separate" && (
                        <span className="inline-flex items-center gap-1 text-[#e5534b]">
                          <HelpCircle className="w-3 h-3" /> SEPARATE
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-[#8b8f94] whitespace-nowrap">
                      {row.timestamp.slice(11, 19)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
