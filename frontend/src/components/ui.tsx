import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  Search,
  Zap,
  BarChart3,
  Download,
  Settings,
  Menu,
  X,
  ChevronRight,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { path: '/report', label: 'Report Incident', icon: AlertTriangle },
  { path: '/explorer', label: 'Incident Explorer', icon: Search },
  { path: '/triage', label: 'AI Triage', icon: Zap },
  { path: '/intelligence', label: 'Model Intelligence', icon: BarChart3 },
  { path: '/reports', label: 'Reports & Exports', icon: Download },
  { path: '/settings', label: 'Settings', icon: Settings },
];

interface NavigationProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export function Navigation({ sidebarOpen, setSidebarOpen }: NavigationProps) {
  const navigate = useNavigate();

  return (
    <>
      {/* Top Nav */}
      <nav className="nav">
        <div className="nav-inner">
          <a
            className="nav-brand"
            onClick={() => navigate('/')}
            style={{ cursor: 'pointer' }}
          >
            <div className="nav-brand-mark">S</div>
            <div className="nav-brand-text">
              <span className="nav-brand-name">Sentinel AI</span>
              <span className="nav-brand-sub">AI Incident Governance</span>
            </div>
          </a>

          <div className="nav-actions">
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => navigate('/report')}
              style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}
            >
              <AlertTriangle size={14} />
              Report
            </button>
            <button
              className="btn btn-icon btn-ghost"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle navigation"
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="eyebrow sidebar-section">Navigation</div>
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
            onClick={() => {
              // On mobile, close sidebar after navigation
              if (window.innerWidth < 768) setSidebarOpen(false);
            }}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </aside>
    </>
  );
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
      <div>
        {eyebrow && <div className="page-eyebrow">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

export function LoadingSkeleton({ rows = 3, height = 48 }: { rows?: number; height?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: `${height}px`, borderRadius: '8px' }} />
      ))}
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
      {action}
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="alert alert-error" role="alert">
      <AlertTriangle size={16} />
      <span>{message}</span>
    </div>
  );
}

// ─── Breadcrumb ───────────────────────────────────────────────────────────────

interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  const navigate = useNavigate();
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '1rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
      {items.map((item, i) => (
        <React.Fragment key={i}>
          {i > 0 && <ChevronRight size={12} />}
          {item.href ? (
            <button
              onClick={() => navigate(item.href!)}
              style={{ color: 'var(--accent-cyan)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 'inherit', padding: 0 }}
            >
              {item.label}
            </button>
          ) : (
            <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ─── Metric Card ──────────────────────────────────────────────────────────────

interface MetricCardProps {
  label: string;
  value: number | string;
  sub?: string;
  color?: string;
}

export function MetricCard({ label, value, sub, color }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={color ? { color } : undefined}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

// ─── Pagination ───────────────────────────────────────────────────────────────

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages: (number | '...')[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push('...');
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i);
    if (page < totalPages - 2) pages.push('...');
    pages.push(totalPages);
  }

  return (
    <div className="pagination">
      <button
        className="pagination-btn"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        ‹
      </button>
      {pages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} style={{ color: 'var(--text-muted)', padding: '0 0.25rem' }}>…</span>
        ) : (
          <button
            key={p}
            className={`pagination-btn ${p === page ? 'active' : ''}`}
            onClick={() => onPageChange(p as number)}
          >
            {p}
          </button>
        ),
      )}
      <button
        className="pagination-btn"
        disabled={page === totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        ›
      </button>
    </div>
  );
}

// ─── Demo badge ───────────────────────────────────────────────────────────────

export function DemoBadge() {
  return <span className="demo-label">⚠ SYNTHETIC DEMO</span>;
}
