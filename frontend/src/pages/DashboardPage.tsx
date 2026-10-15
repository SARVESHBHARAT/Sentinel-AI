import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { AlertTriangle, TrendingUp, CheckCircle, Clock } from 'lucide-react';
import api from '../api/client';
import type { OverviewResponse } from '../api/client';
import {
  PageHeader, LoadingSkeleton, ErrorState, MetricCard,
} from '../components/ui';
import { formatCategory, formatLabel } from '../utils/format';

const CHART_COLORS = [
  '#f5f5f5', '#38bdf8', '#34d399', '#fbbf24', '#f87171',
  '#94a3b8', '#60a5fa', '#e2e8f0',
];

const CUSTOM_TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border-default)',
  borderRadius: '8px',
  padding: '0.625rem 0.875rem',
  fontSize: '0.8125rem',
  color: 'var(--text-primary)',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.overview()
      .then(setData)
      .catch((e) => setError(e.message ?? 'Failed to load overview'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div>
        <PageHeader eyebrow="Dashboard" title="Overview" />
        <LoadingSkeleton rows={4} height={120} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <PageHeader eyebrow="Dashboard" title="Overview" />
        <ErrorState message={error ?? 'No data available'} />
      </div>
    );
  }

  // Prepare chart data
  const categoryData = Object.entries(data.by_category).map(([k, v]) => ({
    name: formatCategory(k),
    value: v,
  }));

  const severityData = Object.entries(data.by_severity).map(([k, v]) => ({
    name: formatLabel(k),
    value: v,
  }));

  const statusData = Object.entries(data.by_status).map(([k, v]) => ({
    name: formatLabel(k),
    value: v,
  }));

  const verificationData = Object.entries(data.by_verification).map(([k, v]) => ({
    name: formatLabel(k),
    value: v,
  }));

  const trendData = Object.entries(data.trend)
    .slice(-30)
    .map(([date, count]) => ({ date, count }));

  return (
    <div>
      <PageHeader
        eyebrow="Dashboard"
        title="Overview"
        description="Real-time metrics from the incident database."
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/report')}>
            <AlertTriangle size={14} />
            Report Incident
          </button>
        }
      />

      {/* Metric cards */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <MetricCard
          label="Total Incidents"
          value={data.total}
          sub="All time"
        />
        <MetricCard
          label="Open Cases"
          value={data.open_incidents}
          sub="Submitted + Under Review + Action Required"
          color="var(--accent-cyan)"
        />
        <MetricCard
          label="High / Critical"
          value={data.high_critical}
          sub="Severity threshold"
          color="var(--severity-high)"
        />
        <MetricCard
          label="Awaiting Review"
          value={data.awaiting_review}
          sub="Submitted status"
          color="var(--text-accent)"
        />
      </div>

      {/* Trend chart */}
      {trendData.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h4 style={{ marginBottom: '1.25rem' }}>
            <TrendingUp size={16} style={{ display: 'inline', marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
            Reporting Trend
          </h4>
          <div className="chart-container">
            <ResponsiveContainer>
              <AreaChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f5f5f5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f5f5f5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={CUSTOM_TOOLTIP_STYLE}
                  labelStyle={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#f5f5f5"
                  strokeWidth={1.5}
                  fill="url(#trendGradient)"
                  dot={false}
                  name="Incidents"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Distribution charts */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        {/* Category */}
        <div className="card">
          <h4 style={{ marginBottom: '1.25rem' }}>By Category</h4>
          {categoryData.length > 0 ? (
            <div className="chart-container-sm">
              <ResponsiveContainer>
                <BarChart data={categoryData} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={130} />
                  <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
                  <Bar dataKey="value" radius={[0, 3, 3, 0]} name="Count">
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No data</p>
          )}
        </div>

        {/* Severity */}
        <div className="card">
          <h4 style={{ marginBottom: '1.25rem' }}>By Severity</h4>
          {severityData.length > 0 ? (
            <div className="chart-container-sm">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={severityData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={72}
                    paddingAngle={2}
                  >
                    {severityData.map((entry, i) => {
                      const SEVERITY_COLORS: Record<string, string> = {
                        Critical: '#ef4444',
                        High: '#f97316',
                        Medium: '#eab308',
                        Low: '#22c55e',
                        'Not Assessed': '#6b7280',
                      };
                      return <Cell key={i} fill={SEVERITY_COLORS[entry.name] ?? CHART_COLORS[i]} />;
                    })}
                  </Pie>
                  <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
                  <Legend
                    iconSize={8}
                    iconType="circle"
                    wrapperStyle={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No data</p>
          )}
        </div>
      </div>

      {/* Status + Verification */}
      <div className="grid-2">
        <div className="card">
          <h4 style={{ marginBottom: '1.25rem' }}>
            <Clock size={15} style={{ display: 'inline', marginRight: '0.5rem', color: 'var(--text-accent)' }} />
            Incident Status
          </h4>
          {statusData.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {statusData.map(({ name, value }, i) => {
                const pct = data.total ? Math.round((value / data.total) * 100) : 0;
                return (
                  <div key={name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem', fontSize: '0.8rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{value} ({pct}%)</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${pct}%`,
                          background: CHART_COLORS[i % CHART_COLORS.length],
                          borderRadius: 2,
                          transition: 'width 0.6s ease',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No data</p>
          )}
        </div>

        <div className="card">
          <h4 style={{ marginBottom: '1.25rem' }}>
            <CheckCircle size={15} style={{ display: 'inline', marginRight: '0.5rem', color: '#22c55e' }} />
            Verification Status
          </h4>
          {verificationData.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {verificationData.map(({ name, value }, i) => {
                const pct = data.total ? Math.round((value / data.total) * 100) : 0;
                const VCOLORS: Record<string, string> = {
                  Verified: '#22c55e',
                  Disputed: '#ef4444',
                  'Ai Assessed': '#d4d4d8',
                  'Human Reviewed': '#38bdf8',
                  Reported: '#a3a3a3',
                  Unverified: '#71717a',
                };
                return (
                  <div key={name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem', fontSize: '0.8rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{value} ({pct}%)</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${pct}%`,
                          background: VCOLORS[name] ?? CHART_COLORS[i],
                          borderRadius: 2,
                          transition: 'width 0.6s ease',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No data</p>
          )}
        </div>
      </div>
    </div>
  );
}
