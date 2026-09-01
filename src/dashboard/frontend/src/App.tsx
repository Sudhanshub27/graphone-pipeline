import React, { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { CommandPalette } from "./components/CommandPalette";
import { OverviewPage } from "./pages/OverviewPage";
import { DataBrowserPage } from "./pages/DataBrowserPage";
import { EntityResolutionPage } from "./pages/EntityResolutionPage";
import { PipelineLogsPage } from "./pages/PipelineLogsPage";

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<string>("overview");
  const [selectedEntityCategory, setSelectedEntityCategory] = useState<string>("startup");
  const [cmdKOpen, setCmdKOpen] = useState<boolean>(false);
  const [stats, setStats] = useState<any>(null);

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRunPipeline = async () => {
    try {
      await fetch("/api/run", { method: "POST" });
      await fetchStats();
    } catch (e) {
      console.error("Failed to trigger pipeline run", e);
    }
  };

  const handleNavigateFromCmdK = (route: string, entityType?: string) => {
    setCurrentRoute(route);
    if (entityType) {
      setSelectedEntityCategory(entityType);
    }
  };

  const handleNavigateEntityFromOverview = (entityType: string) => {
    setSelectedEntityCategory(entityType);
    setCurrentRoute("browser");
  };

  return (
    <div className="min-h-screen bg-[#0a0b0d] text-[#e6e6e6] flex">
      {/* Command Palette Modal */}
      <CommandPalette
        open={cmdKOpen}
        onOpenChange={setCmdKOpen}
        onSelectNav={handleNavigateFromCmdK}
      />

      {/* Fixed 220px Sidebar */}
      <Sidebar
        currentRoute={currentRoute}
        onNavigate={(route) => setCurrentRoute(route)}
        onOpenCmdK={() => setCmdKOpen(true)}
      />

      {/* Main Content Area (Margin Left 220px) */}
      <div className="flex-1 ml-[220px] flex flex-col min-w-0 min-h-screen">
        {/* Sticky Topbar */}
        <Topbar
          status={stats?.status || "idle"}
          lastRunAt={stats?.lastRunAt || ""}
          onRunPipeline={handleRunPipeline}
        />

        {/* Page Container */}
        <main className="flex-1 p-6 max-w-[1600px] w-full mx-auto">
          {currentRoute === "overview" && (
            <OverviewPage
              stats={stats}
              onNavigateEntity={handleNavigateEntityFromOverview}
            />
          )}

          {currentRoute === "browser" && (
            <DataBrowserPage initialEntity={selectedEntityCategory} />
          )}

          {currentRoute === "resolution" && <EntityResolutionPage />}

          {currentRoute === "logs" && <PipelineLogsPage />}
        </main>
      </div>
    </div>
  );
};
export default App;
