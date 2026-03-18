import { Routes, Route } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import DashboardHome from "./DashboardHome";
import PersonaEngine from "./PersonaEngine";
import ContentStudio from "./ContentStudio";
import Connections from "./Connections";
import ContentCalendar from "./ContentCalendar";
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
          <Route path="/repurpose" element={<><TopBar title="Repurpose Agent" /><ComingSoon title="Repurpose Agent" desc="Transform one piece of content into 6 platform-native variants." sprint="8" /></>} />
          <Route path="/calendar" element={<><TopBar title="Content Calendar" /><ContentCalendar /></>} />
          <Route path="/analytics" element={<><TopBar title="Analytics" /><ComingSoon title="Analytics" desc="Performance intelligence and learning loop insights." sprint="9" /></>} />
          <Route path="/library" element={<><TopBar title="Content Library" /><ComingSoon title="Content Library" desc="All your drafts, scheduled, and published content in one place." sprint="8" /></>} />
          <Route path="/connections" element={<><TopBar title="Platform Connections" /><Connections /></>} />
          <Route path="/settings" element={<><TopBar title="Settings" /><ComingSoon title="Settings" desc="Account, billing, and preferences." sprint="10" /></>} />
        </Routes>
      </div>
    </div>
  );
}
