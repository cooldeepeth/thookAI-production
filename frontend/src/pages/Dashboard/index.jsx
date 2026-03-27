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

export default function Dashboard() {
  return (
    <div className="flex bg-[#050505] min-h-screen" data-testid="dashboard-layout">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        <Routes>
          <Route path="/" element={<><TopBar title="Dashboard" /><DashboardHome /></>} />
          <Route path="/studio" element={<><TopBar title="Content Studio" /><ContentStudio /></>} />
          <Route path="/persona" element={<><TopBar title="Persona Engine" /><PersonaEngine /></>} />
          <Route path="/repurpose" element={<><TopBar title="Repurpose Agent" /><RepurposeAgent /></>} />
          <Route path="/calendar" element={<><TopBar title="Content Calendar" /><ContentCalendar /></>} />
          <Route path="/analytics" element={<><TopBar title="Analytics" /><Analytics /></>} />
          <Route path="/library" element={<><TopBar title="Content Library" /><ContentLibrary /></>} />
          <Route path="/connections" element={<><TopBar title="Platform Connections" /><Connections /></>} />
          <Route path="/agency" element={<><TopBar title="Agency Workspace" /><AgencyWorkspace /></>} />
          <Route path="/templates" element={<><TopBar title="Templates Marketplace" /><Templates /></>} />
          <Route path="/templates/:templateId" element={<><TopBar title="Template Detail" /><TemplateDetail /></>} />
          <Route path="/campaigns" element={<><TopBar title="Campaigns" /><Campaigns /></>} />
          <Route path="/settings" element={<><TopBar title="Settings" /><Settings /></>} />
        </Routes>
      </div>
    </div>
  );
}
