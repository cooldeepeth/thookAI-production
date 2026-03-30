import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import DashboardHome from "./DashboardHome";
import PersonaEngine from "./PersonaEngine";
import ContentStudio from "./ContentStudio";
import Connections from "./Connections";
import ContentCalendar from "./ContentCalendar";
import RepurposeAgent from "./RepurposeAgent";
import ContentLibrary from "./ContentLibrary";
import Analytics from "./Analytics";
import Settings from "./Settings";
import AgencyWorkspace from "./AgencyWorkspace";
import Templates from "./Templates";
import TemplateDetail from "./TemplateDetail";
import Campaigns from "./Campaigns";
import ComingSoon from "./ComingSoon";
import Admin from "./Admin";
import AdminUsers from "./AdminUsers";

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex bg-[#050505] min-h-screen" data-testid="dashboard-layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        <Routes>
          <Route path="/" element={<><TopBar onMenuClick={() => setSidebarOpen(true)} title="Dashboard" /><DashboardHome /></>} />
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
      </div>
    </div>
  );
}
