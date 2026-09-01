import React, { useState } from "react";
import { Play, Loader2, Clock } from "lucide-react";

interface TopbarProps {
  status: string; // "idle" | "running" | "failed"
  lastRunAt: string;
  onRunPipeline: () => Promise<void>;
}

export const Topbar: React.FC<TopbarProps> = ({
  status,
  lastRunAt,
  onRunPipeline,
}) => {
  const [loading, setLoading] = useState(false);

  const handleRunClick = async () => {
    setLoading(true);
    try {
      await onRunPipeline();
    } finally {
      setLoading(false);
    }
  };

  const getStatusDotColor = () => {
    switch (status) {
      case "running":
        return "bg-[#6e9fe0] animate-pulse";
      case "failed":
        return "bg-[#e5534b]";
      case "idle":
      default:
        return "bg-[#7ee787]";
    }
  };

  const formattedDate = lastRunAt
    ? new Date(lastRunAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "N/A";

  return (
    <header className="h-14 bg-[#131417] border-b border-[#1f2124] flex items-center justify-between px-6 select-none sticky top-0 z-20">
      {/* Run Status Pill */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#0a0b0d] border border-[#1f2124]">
          <span className={`w-2 h-2 rounded-full ${getStatusDotColor()}`} />
          <span className="font-mono text-xs uppercase tracking-wider text-[#e6e6e6]">
            {status === "running" ? "RUNNING PIPELINE..." : `STATUS: ${status.toUpperCase()}`}
          </span>
        </div>

        <div className="flex items-center gap-1.5 font-mono text-xs text-[#8b8f94]">
          <Clock className="w-3.5 h-3.5 text-[#4a4d52]" />
          <span>Last Run: {formattedDate}</span>
        </div>
      </div>

      {/* Manual Trigger Button */}
      <button
        onClick={handleRunClick}
        disabled={status === "running" || loading}
        className="h-8 px-3.5 rounded bg-[#7ee787] hover:bg-[#6ed677] active:bg-[#5fc568] disabled:opacity-50 text-[#0a0b0d] font-mono text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:cursor-not-allowed"
      >
        {status === "running" || loading ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Executing...</span>
          </>
        ) : (
          <>
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run Pipeline</span>
          </>
        )}
      </button>
    </header>
  );
};
