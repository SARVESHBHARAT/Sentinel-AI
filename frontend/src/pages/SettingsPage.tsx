import { useState, useEffect } from 'react';
import {
  Database,
  Cpu,
  Trash2,
  DatabaseZap,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Shield,
  Info,
} from 'lucide-react';
import api from '../api/client';
import type { SettingsResponse } from '../api/client';
import { PageHeader, LoadingSkeleton, ErrorState } from '../components/ui';

export default function SettingsPage() {
  const [config, setConfig] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Maintenance states
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const fetchSettings = () => {
    setLoading(true);
    api.settings
      .get()
      .then(setConfig)
      .catch((err) => setError(err.message || 'Failed to load system settings.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleResetDemo = async () => {
    if (!confirmReset) return;
    setResetting(true);
    setStatusMessage(null);
    try {
      const res = await api.settings.resetDemo();
      setStatusMessage({ type: 'success', text: res.message });
      setConfirmReset(false);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Demo reset failed: ${err.message}` });
    } finally {
      setResetting(false);
    }
  };

  const handleSeedDemo = async () => {
    setSeeding(true);
    setStatusMessage(null);
    try {
      const res = await api.settings.seedDemo();
      setStatusMessage({ type: 'success', text: res.message });
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Demo seeding failed: ${err.message}` });
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="System Administration"
        title="Settings & Maintenance"
        description="Configuration status, database health, rate limit telemetry, and safe local dataset controls."
      />

      {error && <ErrorState message={error} />}

      {statusMessage && (
        <div
          className={`alert ${statusMessage.type === 'success' ? 'alert-success' : statusMessage.type === 'error' ? 'alert-error' : 'alert-info'}`}
          style={{ marginBottom: '1.5rem' }}
        >
          {statusMessage.type === 'success' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {loading && !config ? (
        <LoadingSkeleton rows={4} height={90} />
      ) : config ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          
          {/* AI Intelligence Configuration Card */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <Cpu size={18} color="var(--text-primary)" />
              <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>AI Intelligence Pipeline</h2>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Target Model</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--text-primary)' }}>{config.openai_model}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>API Key Status</span>
                <span className={`badge ${config.has_api_key ? 'badge-verified' : 'badge-neutral'}`}>
                  {config.has_api_key ? 'Configured & Active' : 'Not Configured (Fallback Mode)'}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Effective Operational Mode</span>
                <span className={`badge ${config.effective_demo_mode ? 'badge-in_progress' : 'badge-verified'}`}>
                  {config.effective_demo_mode ? 'Deterministic Demo Mode' : 'Live Neural Triage'}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Observatory Min Sample</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                  {config.model_intelligence_min_sample} records
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                {config.effective_demo_mode ? (
                  <div className="alert alert-warning" style={{ padding: '0.75rem' }}>
                    <Info size={14} />
                    <span>Demo mode is active. AI assessments are generated deterministically and labelled as synthetic output.</span>
                  </div>
                ) : (
                  <div className="alert alert-info" style={{ padding: '0.75rem' }}>
                    <Shield size={14} />
                    <span>Live-model configuration is enabled. Human reviewer determination remains strictly mandatory before classification takes effect.</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Database & Storage Card */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <Database size={18} color="var(--accent-cyan)" />
              <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>Database & Storage Health</h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>SQLite Database File</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--accent-cyan)', wordBreak: 'break-all' }}>
                  {config.database_path}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Foreign Key Constraints</span>
                <span className="badge badge-verified">PRAGMA foreign_keys = ON</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Write Permissions</span>
                <span className={`badge ${config.read_only ? 'badge-critical' : 'badge-verified'}`}>
                  {config.read_only ? 'READ ONLY (Locked)' : 'Read-Write (Active)'}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Submission Rate Limit</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                  {config.submission_rate_limit} req / {config.submission_rate_window_seconds}s
                </span>
              </div>

              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.5rem 0 0 0' }}>
                All transactions utilize WAL journal mode and immediate-mode concurrency control to avoid locked database errors.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Maintenance Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        
        {/* Synthetic Demo Dataset Seeding */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <DatabaseZap size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>Synthetic Demo Dataset</h2>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Populate fictional demo incidents across major providers, model families, and versions for evaluation and observatory testing. Seeding is idempotent and safe.
          </p>

          <button
            className="btn btn-primary"
            onClick={handleSeedDemo}
            disabled={seeding || config?.read_only}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {seeding ? <RefreshCw size={15} className="spin" /> : <DatabaseZap size={15} />}
            {seeding ? 'Seeding Demo Records...' : 'Seed Synthetic Demo Dataset'}
          </button>
        </div>

        {/* Demo Data Reset Maintenance */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Trash2 size={18} color="var(--color-critical)" />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>Reset Demo Records</h2>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Safely purges only records marked as demo data. Real user reports and human reviews are preserved intact and unaffected.
          </p>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.8125rem',
              color: 'var(--text-secondary)',
              marginBottom: '1.25rem',
              userSelect: 'none',
            }}
          >
            <input
              type="checkbox"
              checked={confirmReset}
              onChange={(e) => setConfirmReset(e.target.checked)}
              style={{ width: '1rem', height: '1rem', accentColor: 'var(--color-critical)' }}
            />
            <span>I understand this removes only synthetic demo records</span>
          </label>

          <button
            className="btn btn-danger"
            onClick={handleResetDemo}
            disabled={!confirmReset || resetting || config?.read_only}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {resetting ? <RefreshCw size={15} className="spin" /> : <Trash2 size={15} />}
            {resetting ? 'Removing Demo Records...' : 'Reset Demo Records'}
          </button>
        </div>

      </div>
    </div>
  );
}
