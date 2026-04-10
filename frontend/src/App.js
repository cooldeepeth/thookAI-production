import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/components/ui/UIComponents";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import Dashboard from "@/pages/Dashboard";
import OnboardingWizard from "@/pages/Onboarding";
import PersonaCardPublic from "@/pages/Public/PersonaCardPublic";
import ViralCard from "@/pages/ViralCard";

function ProtectedRoute({ children, requireOnboarding = false }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-lime border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-500 text-sm">Loading ThookAI...</span>
        </div>
      </div>
    );
  if (!user) return <Navigate to="/auth" replace />;
  // Redirect to onboarding if user hasn't completed it (onboarding route itself doesn't set this flag)
  if (requireOnboarding && !user.onboarding_completed) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/creator/:shareToken" element={<PersonaCardPublic />} />
      <Route path="/p/:shareToken" element={<PersonaCardPublic />} />
      <Route path="/discover" element={<ViralCard />} />
      <Route path="/discover/:cardId" element={<ViralCard />} />
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingWizard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/*"
        element={
          <ProtectedRoute requireOnboarding>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRouter />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
