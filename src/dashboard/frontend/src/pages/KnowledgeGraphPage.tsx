import React, { useEffect, useState } from "react";
import { Share2, Code, Database, Check, Copy, ExternalLink, RefreshCw } from "lucide-react";

export const KnowledgeGraphPage: React.FC = () => {
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [], summary: {} });
  const [cypherScript, setCypherScript] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const [gRes, cRes] = await Promise.all([
        fetch("/api/graph"),
        fetch("/api/graph/export"),
      ]);
      if (gRes.ok) setGraphData(await gRes.json());
      if (cRes.ok) setCypherScript(await cRes.text());
    } catch (e) {
      console.error("Failed to load Knowledge Graph", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const handleCopyCypher = () => {
    navigator.clipboard.writeText(cypherScript);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLabelColor = (label: string) => {
    switch (label) {
      case "Startup":
        return "bg-[#7ee787]/10 text-[#7ee787] border-[#7ee787]/30";
      case "Product":
        return "bg-[#6e9fe0]/10 text-[#6e9fe0] border-[#6e9fe0]/30";
      case "ResearchPaper":
        return "bg-[#e8b339]/10 text-[#e8b339] border-[#e8b339]/30";
      case "Job":
        return "bg-[#e5534b]/10 text-[#e5534b] border-[#e5534b]/30";
      default:
        return "bg-[#8b8f94]/10 text-[#8b8f94] border-[#8b8f94]/30";
    }
  };

  return (
    <div className="space-y-6 select-none">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold font-mono text-[#e6e6e6] flex items-center gap-2">
            <Share2 className="w-5 h-5 text-[#7ee787]" />
            KNOWLEDGE GRAPH & RELATIONSHIP ENGINE
          </h1>
          <p className="text-xs text-[#8b8f94] mt-1 font-mono">
            Extracted node topologies, relational graph triples, and Neo4j Cypher export
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/metrics"
            target="_blank"
            rel="noopener noreferrer"
            className="h-8 px-3 rounded bg-[#0a0b0d] hover:bg-[#1f2124] border border-[#1f2124] text-[#7ee787] font-mono text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open /metrics</span>
          </a>

          <button
            onClick={fetchGraph}
            className="h-8 px-3 rounded bg-[#131417] hover:bg-[#1f2124] border border-[#1f2124] text-[#e6e6e6] font-mono text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Graph</span>
          </button>
        </div>
      </div>

      {/* Top Stat Summary Cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-4 rounded bg-[#131417] border border-[#1f2124]">
          <span className="text-xs text-[#8b8f94] font-mono">Total Graph Nodes</span>
          <div className="text-2xl font-bold text-[#e6e6e6] mt-1">
            {graphData.nodes?.length || 0}
          </div>
        </div>
        <div className="p-4 rounded bg-[#131417] border border-[#1f2124]">
          <span className="text-xs text-[#8b8f94] font-mono">Relational Triples / Edges</span>
          <div className="text-2xl font-bold text-[#7ee787] mt-1">
            {graphData.edges?.length || 0}
          </div>
        </div>
        <div className="p-4 rounded bg-[#131417] border border-[#1f2124]">
          <span className="text-xs text-[#8b8f94] font-mono">Primary Relation</span>
          <div className="text-2xl font-bold text-[#6e9fe0] mt-1 font-mono">PRODUCES</div>
        </div>
        <div className="p-4 rounded bg-[#131417] border border-[#1f2124]">
          <span className="text-xs text-[#8b8f94] font-mono">Secondary Relation</span>
          <div className="text-2xl font-bold text-[#e8b339] mt-1 font-mono">POSTED_BY</div>
        </div>
      </div>

      {/* Main Two-Column View: Graph Triples & Neo4j Cypher Script */}
      <div className="grid grid-cols-2 gap-4">
        {/* Knowledge Triples List */}
        <div className="p-5 rounded bg-[#131417] border border-[#1f2124] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1f2124] pb-3">
            <h2 className="text-xs font-bold font-mono text-[#e6e6e6] flex items-center gap-2">
              <Database className="w-4 h-4 text-[#6e9fe0]" />
              RELATIONAL GRAPH TRIPLES ({graphData.edges?.length || 0})
            </h2>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {graphData.edges && graphData.edges.length > 0 ? (
              graphData.edges.map((edge: any, idx: number) => {
                const srcNode = graphData.nodes.find((n: any) => n.id === edge.source);
                const tgtNode = graphData.nodes.find((n: any) => n.id === edge.target);
                return (
                  <div
                    key={idx}
                    className="p-3 rounded bg-[#0a0b0d] border border-[#1f2124] flex items-center justify-between text-xs font-mono"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] uppercase font-bold ${getLabelColor(
                          srcNode?.label || "Node"
                        )}`}
                      >
                        {srcNode?.name || edge.source}
                      </span>
                      <span className="text-[#7ee787] font-bold text-[11px]">
                        -[{edge.relation}]-&gt;
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] uppercase font-bold ${getLabelColor(
                          tgtNode?.label || "Node"
                        )}`}
                      >
                        {tgtNode?.name || edge.target}
                      </span>
                    </div>

                    <span className="text-[10px] text-[#8b8f94]">
                      {Math.round(edge.confidence * 100)}% Conf
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center text-xs text-[#8b8f94] font-mono">
                No relational graph edges generated yet. Run pipeline to extract entity triples.
              </div>
            )}
          </div>
        </div>

        {/* Neo4j Cypher Export Viewer */}
        <div className="p-5 rounded bg-[#131417] border border-[#1f2124] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1f2124] pb-3">
            <h2 className="text-xs font-bold font-mono text-[#e6e6e6] flex items-center gap-2">
              <Code className="w-4 h-4 text-[#e8b339]" />
              NEO4J CYPHER EXPORT SCRIPT
            </h2>

            <button
              onClick={handleCopyCypher}
              className="px-3 py-1 rounded bg-[#0a0b0d] hover:bg-[#1f2124] border border-[#1f2124] text-[#7ee787] font-mono text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied Cypher!" : "Copy Cypher"}</span>
            </button>
          </div>

          <pre className="p-4 rounded bg-[#0a0b0d] border border-[#1f2124] font-mono text-[11px] text-[#7ee787] max-h-[490px] overflow-auto whitespace-pre-wrap leading-relaxed">
            {cypherScript || "// Loading Cypher export script..."}
          </pre>
        </div>
      </div>
    </div>
  );
};
