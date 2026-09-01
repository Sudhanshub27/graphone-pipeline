import React, { useEffect, useState } from "react";
import { DataTable, ColumnDef } from "../components/DataTable";
import { Download, Search, RefreshCw } from "lucide-react";

interface DataBrowserPageProps {
  initialEntity?: string;
}

export const DataBrowserPage: React.FC<DataBrowserPageProps> = ({
  initialEntity = "startup",
}) => {
  const [activeTab, setActiveTab] = useState<string>(initialEntity);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (initialEntity) setActiveTab(initialEntity);
  }, [initialEntity]);

  const tabs = [
    { id: "startup", label: "Startups" },
    { id: "product", label: "Products" },
    { id: "research_paper", label: "Research Papers" },
    { id: "job", label: "Jobs" },
    { id: "news", label: "News" },
  ];

  const fetchEntityRecords = async (type: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/records/${type}`);
      if (res.ok) {
        const data = await res.json();
        setRecords(data);
      }
    } catch (e) {
      console.error("Failed to fetch records", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntityRecords(activeTab);
  }, [activeTab]);

  // Client-side fuzzy search filter
  const filteredRecords = React.useMemo(() => {
    if (!searchQuery.trim()) return records;
    const q = searchQuery.toLowerCase();
    return records.filter((r) =>
      Object.values(r).some((v) => {
        if (v == null) return false;
        if (typeof v === "string" || typeof v === "number") {
          return String(v).toLowerCase().includes(q);
        }
        if (Array.isArray(v)) {
          return v.some((item) => String(item).toLowerCase().includes(q));
        }
        if (typeof v === "object") {
          return Object.values(v).some((sub) => String(sub).toLowerCase().includes(q));
        }
        return false;
      })
    );
  }, [records, searchQuery]);

  // CSV Exporter
  const handleExportCSV = () => {
    if (filteredRecords.length === 0) return;
    const headers = Object.keys(filteredRecords[0]).filter((k) => k !== "source");
    headers.push("source_name", "source_url");

    const rows = filteredRecords.map((r) => {
      const rowVals = headers.map((h) => {
        if (h === "source_name") return `"${r.source?.name || ""}"`;
        if (h === "source_url") return `"${r.source?.url || ""}"`;
        const val = r[h];
        if (Array.isArray(val)) return `"${val.join("; ")}"`;
        if (typeof val === "string") return `"${val.replace(/"/g, '""')}"`;
        return val ?? "";
      });
      return rowVals.join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `graphone_${activeTab}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Define table column schemas per entity type
  const getColumnsForTab = (): ColumnDef[] => {
    switch (activeTab) {
      case "startup":
        return [
          { key: "name", label: "Company Name" },
          { key: "stage", label: "Stage" },
          { key: "total_funding", label: "Funding", isMonospace: true },
          { key: "founding_year", label: "Founded", isNumeric: true },
          { key: "location", label: "Location" },
          { key: "employee_count", label: "Team Size", isMonospace: true },
          { key: "categories_tags", label: "Categories" },
        ];
      case "product":
        return [
          { key: "name", label: "Product Name" },
          { key: "tagline", label: "Tagline" },
          { key: "maker_company", label: "Maker / Org" },
          { key: "pricing_model", label: "Pricing Tier" },
          { key: "upvotes", label: "Upvotes", isNumeric: true },
          { key: "launch_date", label: "Launched", isMonospace: true },
        ];
      case "research_paper":
        return [
          { key: "title", label: "Paper Title" },
          { key: "journal_conference", label: "Venue / Journal" },
          { key: "citations_count", label: "Citations", isNumeric: true },
          { key: "published_date", label: "Published", isMonospace: true },
          { key: "doi", label: "DOI", isMonospace: true },
        ];
      case "job":
        return [
          { key: "title", label: "Role Title" },
          { key: "company", label: "Company" },
          { key: "location", label: "Location" },
          { key: "job_type", label: "Type" },
          { key: "salary_range", label: "Salary", isMonospace: true },
          { key: "posted_date", label: "Posted", isMonospace: true },
        ];
      case "news":
      default:
        return [
          { key: "title", label: "Headline Title" },
          { key: "author", label: "Author / Reporter" },
          { key: "sentiment_score", label: "Sentiment", isNumeric: true },
          { key: "published_at", label: "Published At", isMonospace: true },
        ];
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header: Tabs + Search + CSV Export */}
      <div className="flex items-center justify-between gap-4 bg-[#131417] p-3 border border-[#1f2124] rounded">
        {/* Entity Selector Tabs */}
        <div className="flex items-center gap-1 bg-[#0a0b0d] p-1 border border-[#1f2124] rounded">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`h-7 px-3 rounded text-xs font-mono transition-colors ${
                activeTab === t.id
                  ? "bg-[#1f2124] text-[#e6e6e6] font-semibold"
                  : "text-[#8b8f94] hover:text-[#e6e6e6]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Search Input & Controls */}
        <div className="flex items-center gap-2 flex-1 justify-end max-w-lg">
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 text-[#4a4d52] absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter records..."
              className="w-full h-8 pl-8 pr-3 bg-[#0a0b0d] border border-[#1f2124] focus:border-[#7ee787] rounded text-xs font-mono text-[#e6e6e6] outline-none transition-colors"
            />
          </div>

          <button
            onClick={() => fetchEntityRecords(activeTab)}
            className="p-1.5 rounded bg-[#0a0b0d] border border-[#1f2124] text-[#8b8f94] hover:text-[#e6e6e6]"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleExportCSV}
            className="h-8 px-3 rounded bg-[#0a0b0d] border border-[#1f2124] hover:border-[#7ee787] text-[#e6e6e6] font-mono text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-[#7ee787]" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Record Counter Summary */}
      <div className="flex items-center justify-between text-xs font-mono text-[#8b8f94] px-1">
        <span>
          Showing <strong className="text-[#e6e6e6]">{filteredRecords.length}</strong> of{" "}
          {records.length} validated records
        </span>
      </div>

      {/* Main Data Table */}
      <DataTable
        columns={getColumnsForTab()}
        data={filteredRecords}
        isLoading={loading}
      />
    </div>
  );
};
