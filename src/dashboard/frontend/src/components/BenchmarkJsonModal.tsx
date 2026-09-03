import React, { useEffect, useState } from "react";
import { FileCode, Copy, Download, X, Check, Loader2, AlertCircle, RefreshCw } from "lucide-react";

interface BenchmarkJsonModalProps {
  open: boolean;
  onClose: () => void;
}

export const BenchmarkJsonModal: React.FC<BenchmarkJsonModalProps> = ({ open, onClose }) => {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/benchmark/latest");
      if (res.status === 404) {
        setReport(null);
        setError("No benchmark report available. Run the evaluation benchmark to generate a report.");
      } else if (!res.ok) {
        setReport(null);
        setError(`Failed to load benchmark report (Status: ${res.status})`);
      } else {
        const data = await res.json();
        setReport(data);
      }
    } catch (err: any) {
      setReport(null);
      setError(err?.message || "Failed to fetch benchmark report");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchBenchmark();
      setCopied(false);
    }
  }, [open]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const jsonString = report ? JSON.stringify(report, null, 2) : "";

  const handleCopy = async () => {
    if (!jsonString) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(jsonString);
      } else {
        throw new Error("Clipboard API unavailable");
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn("Clipboard API failed, using fallback copy", err);
      try {
        const textArea = document.createElement("textarea");
        textArea.value = jsonString;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand("copy");
        document.body.removeChild(textArea);
        if (successful) {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        }
      } catch (fallbackErr) {
        console.error("Fallback copy failed", fallbackErr);
      }
    }
  };

  const handleDownload = () => {
    if (!jsonString) return;
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, "0");
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const filename = `tripwire-benchmark-${timestamp}.json`;

    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="benchmark-modal-title"
    >
      <div
        className="w-full max-w-3xl max-h-[85vh] bg-[#131417] border border-[#1f2124] rounded-lg shadow-2xl flex flex-col overflow-hidden select-text"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2124] bg-[#0a0b0d]">
          <div className="flex items-center gap-2.5">
            <FileCode className="w-4 h-4 text-[#7ee787]" />
            <h3 id="benchmark-modal-title" className="text-sm font-bold font-mono text-[#e6e6e6]">
              Benchmark Report
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded text-[#8b8f94] hover:text-[#e6e6e6] hover:bg-[#1f2124] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 p-5 overflow-hidden flex flex-col justify-center min-h-[260px] bg-[#0a0b0d]/50">
          {loading ? (
            <div className="flex flex-col items-center justify-center space-y-3 py-12">
              <Loader2 className="w-6 h-6 text-[#7ee787] animate-spin" />
              <span className="text-xs font-mono text-[#8b8f94]">Loading benchmark report...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center space-y-3 py-8 text-center px-4">
              <AlertCircle className="w-8 h-8 text-[#e8b339]" />
              <p className="text-xs font-mono text-[#e6e6e6] max-w-md">{error}</p>
              <button
                onClick={fetchBenchmark}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono bg-[#1f2124] text-[#e6e6e6] hover:bg-[#2d3035] transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>
            </div>
          ) : report ? (
            <div className="relative flex-1 max-h-[60vh] overflow-hidden">
              <pre className="w-full h-full max-h-[60vh] overflow-auto p-4 bg-[#0a0b0d] border border-[#1f2124] rounded font-mono text-xs text-[#7ee787] leading-relaxed selection:bg-[#7ee787]/20 selection:text-[#7ee787]">
                {jsonString}
              </pre>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-3.5 border-t border-[#1f2124] bg-[#0a0b0d]">
          {report && !loading && !error && (
            <>
              <button
                onClick={handleCopy}
                disabled={copied}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded text-xs font-mono font-medium bg-[#1f2124] hover:bg-[#2d3035] text-[#e6e6e6] border border-[#2d3035] transition-all cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#7ee787]" />
                    <span className="text-[#7ee787] font-semibold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-[#8b8f94]" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>

              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded text-xs font-mono font-bold bg-[#7ee787] text-[#0a0b0d] hover:bg-[#6ed677] transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download JSON</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
