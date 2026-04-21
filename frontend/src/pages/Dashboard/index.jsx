import { useState, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

const DashboardHome = lazy(() => import("./DashboardHome"));
const PersonaEngine = lazy(() => import("./PersonaEngine"));
const ContentStudio = lazy(() => import("./ContentStudio"));
const Connections = lazy(() => import("./Connections"));
const ContentLibrary = lazy(() => import("./ContentLibrary"));
const Settings = lazy(() => import("./Settings"));

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex bg-[#050505] min-h-screen" data-testid="dashboard-layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        <Suspense fallback={
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="w-8 h-8 border-2 border-lime border-t-transparent rounded-full animate-spin" />
          </div>
        }>
          <Routes>
            <Route path="/" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Dashboard" /><DashboardHome /></>} />
            <Route path="/studio" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Content Studio" /><ContentStudio /></>} />
            <Route path="/persona" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Persona Engine" /><PersonaEngine /></>} />
            <Route path="/library" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Content Library" /><ContentLibrary /></>} />
            <Route path="/connections" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Platform Connections" /><Connections /></>} />
            <Route path="/settings" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Settings" /><Settings /></>} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}
