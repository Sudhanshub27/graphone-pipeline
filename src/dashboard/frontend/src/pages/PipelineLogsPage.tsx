import React, { useEffect, useState } from "react";
import { LogViewer } from "../components/LogViewer";

export const PipelineLogsPage: React.FC = () => {
  const [activeSource, setActiveSource] = useState<string>("scrape.log");
  const [logs, setLogs] = useState<any[]>([]);

  const fetchLogs = async (source: string) => {
    try {
      const res = await fetch(`/api/logs?source=${source}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (e) {
      console.error("Failed to fetch logs", e);
    }
  };

  useEffect(() => {
    fetchLogs(activeSource);
    const interval = setInterval(() => {
      fetchLogs(activeSource);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeSource]);

  return (
    <div className="space-y-4">
      <LogViewer
        logs={logs}
        activeSource={activeSource}
        onSourceChange={(src) => setActiveSource(src)}
        onRefresh={() => fetchLogs(activeSource)}
      />
    </div>
  );
};
