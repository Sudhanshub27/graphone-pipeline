import React, { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown, ExternalLink } from "lucide-react";

export interface ColumnDef {
  key: string;
  label: string;
  isNumeric?: boolean;
  isMonospace?: boolean;
  render?: (row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: ColumnDef[];
  data: any[];
  isLoading?: boolean;
  emptyMessage?: string;
}

export const DataTable: React.FC<DataTableProps> = ({
  columns,
  data,
  isLoading = false,
  emptyMessage = "No records found matching criteria.",
}) => {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDirection === "asc") setSortDirection("desc");
      else {
        setSortKey(null);
        setSortDirection("asc");
      }
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const sortedData = React.useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA === valB) return 0;
      if (valA == null) return 1;
      if (valB == null) return -1;
      if (typeof valA === "number" && typeof valB === "number") {
        return sortDirection === "asc" ? valA - valB : valB - valA;
      }
      return sortDirection === "asc"
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [data, sortKey, sortDirection]);

  return (
    <div className="w-full overflow-x-auto border border-[#1f2124] rounded bg-[#131417]">
      <table className="w-full text-left border-collapse">
        {/* Sticky Header */}
        <thead className="sticky top-0 z-10 bg-[#0a0b0d] border-b border-[#1f2124] select-none">
          <tr>
            {/* Status dot column */}
            <th className="w-8 px-3 py-2.5">
              <span className="sr-only">Status</span>
            </th>

            {columns.map((col) => {
              const isSorted = sortKey === col.key;
              return (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={`px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-[#8b8f94] cursor-pointer hover:text-[#e6e6e6] transition-colors ${
                    col.isNumeric ? "text-right" : "text-left"
                  }`}
                >
                  <div
                    className={`inline-flex items-center gap-1.5 ${
                      col.isNumeric ? "justify-end" : "justify-start"
                    }`}
                  >
                    <span>{col.label}</span>
                    {isSorted ? (
                      sortDirection === "asc" ? (
                        <ArrowUp className="w-3 h-3 text-[#7ee787]" />
                      ) : (
                        <ArrowDown className="w-3 h-3 text-[#7ee787]" />
                      )
                    ) : (
                      <ArrowUpDown className="w-3 h-3 text-[#4a4d52] opacity-0 hover:opacity-100 transition-opacity" />
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody className="divide-y divide-[#1f2124]/60 text-xs">
          {isLoading ? (
            <tr>
              <td colSpan={columns.length + 1} className="py-12 text-center text-[#8b8f94] font-mono">
                Loading records...
              </td>
            </tr>
          ) : sortedData.length === 0 ? (
            <tr>
              <td colSpan={columns.length + 1} className="py-12 text-center text-[#8b8f94] font-mono">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, idx) => (
              <tr
                key={row.id || idx}
                className="hover:bg-[#191b1f] transition-colors group"
              >
                {/* Validation Status Dot */}
                <td className="px-3 py-3 text-center">
                  <span className="inline-block w-2 h-2 rounded-full bg-[#7ee787]" title="Validated Record" />
                </td>

                {columns.map((col) => {
                  const rawVal = row[col.key];
                  return (
                    <td
                      key={col.key}
                      className={`px-4 py-3 text-[#e6e6e6] whitespace-nowrap ${
                        col.isNumeric || col.isMonospace ? "font-mono tabular-nums" : ""
                      } ${col.isNumeric ? "text-right" : "text-left"}`}
                    >
                      {col.render ? (
                        col.render(row)
                      ) : Array.isArray(rawVal) ? (
                        <div className="flex flex-wrap gap-1">
                          {rawVal.slice(0, 3).map((tag, tIdx) => (
                            <span
                              key={tIdx}
                              className="px-1.5 py-0.5 rounded bg-[#0a0b0d] border border-[#1f2124] font-mono text-[10px] text-[#8b8f94]"
                            >
                              {tag}
                            </span>
                          ))}
                          {rawVal.length > 3 && (
                            <span className="font-mono text-[10px] text-[#4a4d52]">
                              +{rawVal.length - 3}
                            </span>
                          )}
                        </div>
                      ) : typeof rawVal === "string" && rawVal.startsWith("http") ? (
                        <a
                          href={rawVal}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#6e9fe0] hover:underline inline-flex items-center gap-1 font-mono text-xs"
                        >
                          <span>{rawVal.replace(/^https?:\/\/(www\.)?/, "").slice(0, 24)}...</span>
                          <ExternalLink className="w-3 h-3 text-[#4a4d52]" />
                        </a>
                      ) : (
                        rawVal ?? <span className="text-[#4a4d52] font-mono">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};
