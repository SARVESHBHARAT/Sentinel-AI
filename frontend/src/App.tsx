import { useState, useEffect } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  useLocation,
  useNavigate,
  Outlet,
} from 'react-router-dom';
import { Navigation } from './components/ui';

// Pages
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import ReportIncidentPage from './pages/ReportPage';
import ExplorerPage from './pages/ExplorerPage';
import IncidentDetailsPage from './pages/IncidentDetailsPage';
import TriagePage from './pages/TriagePage';
import IntelligencePage from './pages/IntelligencePage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <>
      <Navigation sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="layout">
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </>
  );
}

function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <div className="eyebrow" style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
        404 NOT FOUND
      </div>
      <h1 style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: '1rem', color: 'var(--text-primary)' }}>
        Coordinates Unknown
      </h1>
      <p style={{ color: 'var(--text-secondary)', maxWidth: '460px', marginBottom: '2rem' }}>
        The incident telemetry node or governance view you requested does not exist in the active cluster.
      </p>
      <button className="btn btn-primary" onClick={() => navigate('/')}>
        Return to Orbital Command
      </button>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {/* Full-screen experiential hero landing page */}
        <Route path="/" element={<HomePage />} />

        {/* Standard application shell with nav and sidebar */}
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/report" element={<ReportIncidentPage />} />
          <Route path="/explorer" element={<ExplorerPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailsPage />} />
          <Route path="/triage" element={<TriagePage />} />
          <Route path="/intelligence" element={<IntelligencePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
