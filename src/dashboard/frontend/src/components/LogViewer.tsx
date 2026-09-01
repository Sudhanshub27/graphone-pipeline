import React, { useEffect, useRef, useState } from "react";
import { Pause, Play, RefreshCw, Terminal as TerminalIcon } from "lucide-react";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface LogViewerProps {
  logs: LogEntry[];
  activeSource: string;
  onSourceChange: (source: string) => void;
  onRefresh: () => void;
}

export const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  activeSource,
  onSourceChange,
  onRefresh,
}) => {
  const [isPaused, setIsPaused] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom unless user hovers / pauses
  useEffect(() => {
    if (!isPaused && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  const sources = [
    { id: "scrape.log", label: "scrape.log" },
    { id: "llm_extraction.log", label: "llm_extraction.log" },
    { id: "entity_resolution.log", label: "entity_resolution.log" },
  ];

  const getLevelBadgeColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "ERROR":
        return "text-[#e5534b] border-[#e5534b]/30 bg-[#e5534b]/10";
      case "WARN":
      case "WARNING":
        return "text-[#e8b339] border-[#e8b339]/30 bg-[#e8b339]/10";
      case "INFO":
      default:
        return "text-[#8b8f94] border-[#1f2124] bg-[#131417]";
    }
  };

  return (
    <div className="w-full flex flex-col h-[calc(100vh-140px)] border border-[#1f2124] rounded bg-[#0a0b0d] overflow-hidden font-mono text-xs">
      {/* Header bar */}
      <div className="h-10 px-4 bg-[#131417] border-b border-[#1f2124] flex items-center justify-between select-none">
        {/* Source Selector Tabs */}
        <div className="flex items-center gap-1">
          <TerminalIcon className="w-3.5 h-3.5 text-[#7ee787] mr-2" />
          {sources.map((src) => (
            <button
              key={src.id}
              onClick={() => onSourceChange(src.id)}
              className={`h-7 px-2.5 rounded text-[11px] font-mono transition-colors ${
                activeSource === src.id
                  ? "bg-[#0a0b0d] border border-[#1f2124] text-[#e6e6e6]"
                  : "text-[#8b8f94] hover:text-[#e6e6e6]"
              }`}
            >
              {src.label}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#4a4d52]">Live tailing (3s poll)</span>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`h-6 px-2 rounded border text-[10px] flex items-center gap-1 ${
              isPaused
                ? "border-[#e8b339]/40 text-[#e8b339] bg-[#e8b339]/10"
                : "border-[#1f2124] text-[#8b8f94] hover:text-[#e6e6e6]"
            }`}
          >
            {isPaused ? <Play className="w-2.5 h-2.5" /> : <Pause className="w-2.5 h-2.5" />}
            <span>{isPaused ? "PAUSED" : "PAUSE"}</span>
          </button>
          <button
            onClick={onRefresh}
            className="p-1 rounded text-[#8b8f94] hover:text-[#e6e6e6] hover:bg-[#1f2124]"
            title="Refresh logs"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Terminal Content Body */}
      <div
        ref={logContainerRef}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
        className="flex-1 p-4 overflow-y-auto space-y-1.5 leading-relaxed bg-[#0a0b0d] selection:bg-[#7ee787]/20"
      >
        {logs.length === 0 ? (
          <div className="py-8 text-center text-[#4a4d52]">No logs recorded for this source.</div>
        ) : (
          logs.map((log, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 hover:bg-[#131417]/60 px-1 py-0.5 rounded transition-colors"
            >
              {/* Timestamp */}
              <span className="text-[#4a4d52] shrink-0 text-[11px]">
                {log.timestamp.slice(11, 19)}
              </span>

              {/* Log Level Badge */}
              <span
                className={`px-1.5 py-0.2 rounded border text-[10px] font-bold uppercase shrink-0 ${getLevelBadgeColor(
                  log.level
                )}`}
              >
                {log.level}
              </span>

              {/* Message */}
              <span className="text-[#e6e6e6] break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
