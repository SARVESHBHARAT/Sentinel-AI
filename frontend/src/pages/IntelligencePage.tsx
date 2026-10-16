import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Filter,
  Layers,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import api from '../api/client';
import type {
  ModelOverviewMetrics,
  LeaderboardRow,
  ModelDetail,
  EnumsResponse,
} from '../api/client';
import { PageHeader, LoadingSkeleton, ErrorState } from '../components/ui';
import { displayTitle } from '../utils/format';

export default function IntelligencePage() {
  const navigate = useNavigate();

  // Filters state
  const [dataset, setDataset] = useState<'all' | 'demo' | 'genuine'>('all');
  const [providerQuery, setProviderQuery] = useState('');
  const [modelQuery, setModelQuery] = useState('');
  const [period, setPeriod] = useState<string>('all');
  const [category, setCategory] = useState<string>('');
  const [severity, setSeverity] = useState<string>('');
  const [verification, setVerification] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('most_reported');

  // Enums for dropdowns
  const [enums, setEnums] = useState<EnumsResponse | null>(null);

  // Data states
  const [overview, setOverview] = useState<ModelOverviewMetrics | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [selectedModel, setSelectedModel] = useState<{ provider: string; model: string } | null>(null);
  const [modelDetail, setModelDetail] = useState<ModelDetail | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load enums
  useEffect(() => {
    api.enums().then(setEnums).catch(() => {});
  }, []);

  // Compute date_from based on period
  const getDateFrom = useCallback(() => {
    if (period === '30') {
      const d = new Date();
      d.setDate(d.getDate() - 30);
      return d.toISOString().split('T')[0];
    }
    if (period === '90') {
      const d = new Date();
      d.setDate(d.getDate() - 90);
      return d.toISOString().split('T')[0];
    }
    if (period === '365') {
      const d = new Date();
      d.setDate(d.getDate() - 365);
      return d.toISOString().split('T')[0];
    }
    return undefined;
  }, [period]);

  // Load overview & leaderboard
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dateFrom = getDateFrom();
      const params: Record<string, string> = {
        dataset,
        sort_by: sortBy,
      };
      if (category) params.category = category;
      if (severity) params.severity = severity;
      if (verification) params.verification_status = verification;
      if (dateFrom) params.date_from = dateFrom;

      const [metricsData, leaderData] = await Promise.all([
        api.modelIntelligence.overview(params),
        api.modelIntelligence.leaderboard(params),
      ]);

      setOverview(metricsData);

      // Client-side filtering on queries if set
      let filtered = leaderData;
      if (providerQuery.trim()) {
        const q = providerQuery.toLowerCase().trim();
        filtered = filtered.filter((r) => r.provider.toLowerCase().includes(q));
      }
      if (modelQuery.trim()) {
        const q = modelQuery.toLowerCase().trim();
        filtered = filtered.filter((r) => r.affected_model_name.toLowerCase().includes(q));
      }
      setLeaderboard(filtered);

      // Select first model if none selected or if previous selection not in list
      if (filtered.length > 0 && !selectedModel) {
        setSelectedModel({
          provider: filtered[0].provider,
          model: filtered[0].affected_model_name,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load model intelligence data.');
    } finally {
      setLoading(false);
    }
  }, [dataset, sortBy, category, severity, verification, getDateFrom, providerQuery, modelQuery, selectedModel]);

  useEffect(() => {
    fetchData();
  }, [dataset, sortBy, category, severity, verification, period]);

  // Fetch model detail when selected
  useEffect(() => {
    if (!selectedModel) {
      setModelDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    const dateFrom = getDateFrom();
    const params: Record<string, string> = { dataset };
    if (category) params.category = category;
    if (severity) params.severity = severity;
    if (verification) params.verification_status = verification;
    if (dateFrom) params.date_from = dateFrom;

    api.modelIntelligence
      .detail(selectedModel.provider, selectedModel.model, params)
      .then((detail) => {
        if (!cancelled) setModelDetail(detail);
      })
      .catch(() => {
        if (!cancelled) setModelDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedModel, dataset, category, severity, verification, getDateFrom]);

  // Format chart data for top 8 models
  const chartData = leaderboard.slice(0, 8).map((row) => ({
    name: row.affected_model_name.length > 14 ? row.affected_model_name.slice(0, 12) + '…' : row.affected_model_name,
    fullName: `${row.provider} / ${row.affected_model_name}`,
    reports: row.total,
    verified: row.verified,
    high_critical: row.high_critical,
  }));

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Intelligence & Analytics"
        title="AI Model Observatory"
        description="Exact-model comparisons built from reported incidents, verified findings, and severity transparent counts, never arbitrary safety scores."
      />

      {/* Dataset Scope Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: 'All Records (Live + Synthetic)' },
          { key: 'genuine', label: 'Genuine User Reports Only' },
          { key: 'demo', label: 'Synthetic Demo Dataset Only' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setDataset(tab.key as any)}
            className={`btn btn-sm ${dataset === tab.key ? 'btn-primary' : 'btn-ghost'}`}
            style={{ borderRadius: '9999px', fontSize: '0.8125rem' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Dataset Notice Banner */}
      {dataset === 'demo' && (
        <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
          <AlertTriangle size={16} />
          <span>Showing <strong>SYNTHETIC DEMO DATA</strong> only fictional records generated for simulation, not evidence of real model performance.</span>
        </div>
      )}
      {dataset === 'genuine' && (
        <div className="alert alert-info" style={{ marginBottom: '1.5rem' }}>
          <ShieldCheck size={16} />
          <span>Showing <strong>genuine user reports</strong> only. Synthetic demo records are excluded from counts and metrics.</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
          <Filter size={15} />
          <span style={{ fontSize: '0.8125rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Observatory Filters</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Provider Contains</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input input-sm"
                placeholder="e.g. OpenAI, Anthropic"
                value={providerQuery}
                onChange={(e) => setProviderQuery(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Model Contains</label>
            <input
              type="text"
              className="input input-sm"
              placeholder="e.g. GPT-4, Claude"
              value={modelQuery}
              onChange={(e) => setModelQuery(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Reporting Period</label>
            <select
              className="select select-sm"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="all">All Time</option>
              <option value="30">Last 30 Days</option>
              <option value="90">Last 90 Days</option>
              <option value="365">Last 365 Days</option>
            </select>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Category</label>
            <select
              className="select select-sm"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="">All Categories</option>
              {enums?.categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Severity</label>
            <select
              className="select select-sm"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="">All Severities</option>
              {enums?.severities.map((s) => (
                <option key={s} value={s}>
                  {s.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Verification</label>
            <select
              className="select select-sm"
              value={verification}
              onChange={(e) => setVerification(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="">All Verification Statuses</option>
              {enums?.verification_statuses.map((v) => (
                <option key={v} value={v}>
                  {v.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Global Overview Metrics */}
      {loading && !overview ? (
        <LoadingSkeleton rows={2} height={80} />
      ) : overview ? (
        <div style={{ marginBottom: '2rem' }}>
          <div className="eyebrow" style={{ marginBottom: '0.75rem' }}>Dataset Metric Summary</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem' }}>
            <div className="metric-card">
              <div className="metric-label">Matching Incidents</div>
              <div className="metric-value">{overview.total}</div>
              <div className="metric-sub">{dataset} scope</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Distinct Providers</div>
              <div className="metric-value">{overview.distinct_providers}</div>
              <div className="metric-sub">Active vendors</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Distinct Models</div>
              <div className="metric-value">{overview.distinct_models}</div>
              <div className="metric-sub">Tracked families</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Model Versions</div>
              <div className="metric-value">{overview.distinct_versions}</div>
              <div className="metric-sub">Explicit release tags</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Verified Reports</div>
              <div className="metric-value" style={{ color: 'var(--color-verified)' }}>{overview.verified}</div>
              <div className="metric-sub">Independently corroborated</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">High / Critical</div>
              <div className="metric-value" style={{ color: 'var(--color-critical)' }}>{overview.high_critical}</div>
              <div className="metric-sub">Significant risk profile</div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Visual Chart: Top Models Volume */}
      {chartData.length > 0 && (
        <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Incident Volume by Model</h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Top reported AI models in active scope comparing total vs verified reports</p>
            </div>
          </div>
          <div style={{ height: 260, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(21, 21, 21, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="reports" fill="rgba(245, 245, 245, 0.85)" radius={[4, 4, 0, 0]} name="Total Reports" />
                <Bar dataKey="verified" fill="rgba(16, 185, 129, 0.85)" radius={[4, 4, 0, 0]} name="Verified" />
                <Bar dataKey="high_critical" fill="rgba(239, 68, 68, 0.85)" radius={[4, 4, 0, 0]} name="High/Critical" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Main Observatory Content: Leaderboard + Detail Drilldown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1fr) minmax(360px, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
        
        {/* Left: Leaderboard List */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: '0.9375rem', fontWeight: 600 }}>Model Leaderboard</span>
            </div>
            <select
              className="select select-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{ fontSize: '0.75rem' }}
            >
              <option value="most_reported">Most Reported</option>
              <option value="fewest_reported">Fewest Reported</option>
              <option value="most_verified">Most Verified</option>
              <option value="most_high_critical">Most High/Critical</option>
              <option value="model">Model ID (A–Z)</option>
              <option value="provider">Provider (A–Z)</option>
            </select>
          </div>

          {leaderboard.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No models match current filter parameters.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '550px', overflowY: 'auto' }}>
              {leaderboard.map((row) => {
                const isSelected = selectedModel?.provider === row.provider && selectedModel?.model === row.affected_model_name;
                return (
                  <button
                    key={`${row.provider}-${row.affected_model_name}`}
                    onClick={() => setSelectedModel({ provider: row.provider, model: row.affected_model_name })}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem 1rem',
                      borderRadius: '8px',
                      background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                      border: isSelected ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid rgba(255, 255, 255, 0.05)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        {row.provider}
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {row.affected_model_name}
                      </div>
                      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        <span><strong>{row.total}</strong> reports</span>
                        <span>• <strong>{row.verified}</strong> verified</span>
                        {row.high_critical > 0 && (
                          <span style={{ color: 'var(--color-critical)' }}>• {row.high_critical} critical</span>
                        )}
                      </div>
                    </div>
                    <ChevronRight size={16} color={isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Model Detail & Version Breakdown */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Cpu size={16} color="var(--text-primary)" />
            <span style={{ fontSize: '0.9375rem', fontWeight: 600 }}>Model Profile & Version History</span>
          </div>

          {!selectedModel ? (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Select a model from the leaderboard to inspect version breakdown and recent case reports.
            </div>
          ) : detailLoading ? (
            <LoadingSkeleton rows={4} height={50} />
          ) : modelDetail ? (
            <div>
              {/* Header Info */}
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)', marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{modelDetail.provider}</div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0.25rem 0 0.5rem 0', color: 'var(--text-primary)' }}>
                  {modelDetail.affected_model_name}
                </h2>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8125rem' }}>
                  <span>Total recorded: <strong>{modelDetail.total}</strong></span>
                  <span>Minimum sample met: <strong>{modelDetail.sufficient ? 'Yes' : 'No'}</strong></span>
                </div>
              </div>

              {/* Version breakdown */}
              <div style={{ marginBottom: '1.5rem' }}>
                <div className="eyebrow" style={{ marginBottom: '0.5rem' }}>Version Breakdown</div>
                {modelDetail.versions.length === 0 ? (
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>No explicit version identifiers reported.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {modelDetail.versions.map((ver, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.625rem 0.875rem',
                          background: 'rgba(255,255,255,0.02)',
                          borderRadius: '6px',
                          border: '1px solid rgba(255,255,255,0.04)',
                        }}
                      >
                        <div>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                            {ver.affected_model_version || 'Default / Unspecified'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem' }}>
                          <span>{ver.total} reports</span>
                          <span style={{ color: 'var(--color-verified)' }}>{ver.verified} verified</span>
                          <span style={{ color: 'var(--color-critical)' }}>{ver.high_critical} critical</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent incidents linked to this model */}
              <div>
                <div className="eyebrow" style={{ marginBottom: '0.5rem' }}>Recent Incident Filings</div>
                {modelDetail.recent_incidents.length === 0 ? (
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>No recent filings for this model in active filter scope.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {modelDetail.recent_incidents.slice(0, 5).map((inc) => (
                      <div
                        key={inc.incident_id}
                        onClick={() => navigate(`/incidents/${inc.incident_id}`)}
                        style={{
                          padding: '0.625rem 0.875rem',
                          background: 'rgba(255,255,255,0.02)',
                          borderRadius: '6px',
                          border: '1px solid rgba(255,255,255,0.04)',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          transition: 'background 0.15s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                      >
                        <div style={{ maxWidth: '80%' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{inc.incident_id}</span>
                          </div>
                          <div style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {displayTitle(inc.title)}
                          </div>
                        </div>
                        <ChevronRight size={14} color="var(--text-muted)" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
