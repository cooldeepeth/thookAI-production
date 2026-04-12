import { useState, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

const DashboardHome = lazy(() => import("./DashboardHome"));
const PersonaEngine = lazy(() => import("./PersonaEngine"));
const ContentStudio = lazy(() => import("./ContentStudio"));
const Connections = lazy(() => import("./Connections"));
const ContentCalendar = lazy(() => import("./ContentCalendar"));
const RepurposeAgent = lazy(() => import("./RepurposeAgent"));
const ContentLibrary = lazy(() => import("./ContentLibrary"));
const Analytics = lazy(() => import("./Analytics"));
const Settings = lazy(() => import("./Settings"));
const AgencyWorkspace = lazy(() => import("./AgencyWorkspace"));
const Templates = lazy(() => import("./Templates"));
const TemplateDetail = lazy(() => import("./TemplateDetail"));
const Campaigns = lazy(() => import("./Campaigns"));
const ComingSoon = lazy(() => import("./ComingSoon"));
const Admin = lazy(() => import("./Admin"));
const AdminUsers = lazy(() => import("./AdminUsers"));
const StrategyDashboard = lazy(() => import("./StrategyDashboard"));

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
            <Route path="/strategy" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Strategy" /><StrategyDashboard /></>} />
            <Route path="/studio" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Content Studio" /><ContentStudio /></>} />
            <Route path="/persona" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Persona Engine" /><PersonaEngine /></>} />
            <Route path="/repurpose" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Repurpose Agent" /><RepurposeAgent /></>} />
            <Route path="/calendar" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Content Calendar" /><ContentCalendar /></>} />
            <Route path="/analytics" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Analytics" /><Analytics /></>} />
            <Route path="/library" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Content Library" /><ContentLibrary /></>} />
            <Route path="/connections" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Platform Connections" /><Connections /></>} />
            <Route path="/agency" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Agency Workspace" /><AgencyWorkspace /></>} />
            <Route path="/templates" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Templates Marketplace" /><Templates /></>} />
            <Route path="/templates/:templateId" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Template Detail" /><TemplateDetail /></>} />
            <Route path="/campaigns" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Campaigns" /><Campaigns /></>} />
            <Route path="/settings" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Settings" /><Settings /></>} />
            <Route path="/admin" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Admin Dashboard" /><Admin /></>} />
            <Route path="/admin/users" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="User Management" /><AdminUsers /></>} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}
