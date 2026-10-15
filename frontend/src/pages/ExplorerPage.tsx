import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, SlidersHorizontal, ChevronUp, ChevronDown } from 'lucide-react';
import api from '../api/client';
import type { Incident } from '../api/client';
import {
  PageHeader, LoadingSkeleton, ErrorState, EmptyState,
  Pagination, DemoBadge,
} from '../components/ui';
import {
  formatDate, formatCategory, formatLabel,
  severityBadgeClass, verificationBadgeClass, statusBadgeClass,
} from '../utils/format';

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date Created' },
  { value: 'updated_at', label: 'Date Updated' },
  { value: 'report_date', label: 'Report Date' },
  { value: 'severity', label: 'Severity' },
  { value: 'title', label: 'Title' },
];

const SEVERITY_OPTIONS = ['', 'critical', 'high', 'medium', 'low'];
const STATUS_OPTIONS = ['', 'submitted', 'under_review', 'action_required', 'resolved', 'closed'];
const VERIFICATION_OPTIONS = [
  '', 'reported', 'ai_assessed', 'human_reviewed', 'verified', 'disputed', 'unverified',
];

export default function ExplorerPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [q, setQ] = useState(searchParams.get('q') ?? '');
  const [category, setCategory] = useState(searchParams.get('category') ?? '');
  const [severity, setSeverity] = useState(searchParams.get('severity') ?? '');
  const [status, setStatus] = useState(searchParams.get('status') ?? '');
  const [verificationStatus, setVerificationStatus] = useState(searchParams.get('verification_status') ?? '');
  const [provider, setProvider] = useState(searchParams.get('provider') ?? '');
  const [modelName, setModelName] = useState(searchParams.get('affected_model_name') ?? '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') ?? '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') ?? '');
  const [sortBy, setSortBy] = useState(searchParams.get('sort_by') ?? 'created_at');
  const [descending, setDescending] = useState(searchParams.get('descending') !== 'false');
  const [page, setPage] = useState(parseInt(searchParams.get('page') ?? '1', 10));
  const PAGE_SIZE = 20;

  const [debouncedQ, setDebouncedQ] = useState(q);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 350);
    return () => clearTimeout(t);
  }, [q]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.incidents.list({
        q: debouncedQ || undefined,
        category: category || undefined,
        severity: severity || undefined,
        status: status || undefined,
        verification_status: verificationStatus || undefined,
        provider: provider || undefined,
        affected_model_name: modelName || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort_by: sortBy,
        descending,
        page,
        page_size: PAGE_SIZE,
      });
      setIncidents(result.incidents);
      setTotal(result.total);
      setTotalPages(result.total_pages);
    } catch (e: any) {
      setError(e.detail ?? e.message ?? 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, [debouncedQ, category, severity, status, verificationStatus, provider, modelName, dateFrom, dateTo, sortBy, descending, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync URL
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedQ) params.q = debouncedQ;
    if (category) params.category = category;
    if (severity) params.severity = severity;
    if (status) params.status = status;
    if (verificationStatus) params.verification_status = verificationStatus;
    if (provider) params.provider = provider;
    if (modelName) params.affected_model_name = modelName;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (sortBy !== 'created_at') params.sort_by = sortBy;
    if (!descending) params.descending = 'false';
    if (page !== 1) params.page = String(page);
    setSearchParams(params);
  }, [debouncedQ, category, severity, status, verificationStatus, provider, modelName, dateFrom, dateTo, sortBy, descending, page, setSearchParams]);

  function clearFilters() {
    setQ(''); setCategory(''); setSeverity(''); setStatus('');
    setVerificationStatus(''); setProvider(''); setModelName('');
    setDateFrom(''); setDateTo(''); setPage(1);
  }

  const hasFilters = [q, category, severity, status, verificationStatus, provider, modelName, dateFrom, dateTo].some(Boolean);

  return (
    <div>
      <PageHeader
        eyebrow="Investigation"
        title="Incident Explorer"
        description="Search, filter, and investigate the full incident registry."
      />

      {/* Search + controls */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div className="search-bar" style={{ flex: 1, minWidth: 220 }}>
          <Search size={15} className="search-icon" />
          <input
            className="form-input"
            style={{ paddingLeft: '2.5rem' }}
            placeholder="Search ID or title…"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
          />
        </div>
        <button
          className={`btn btn-secondary btn-sm ${showFilters ? 'active' : ''}`}
          onClick={() => setShowFilters((s) => !s)}
          style={{ gap: '0.375rem', borderColor: hasFilters ? 'var(--text-primary)' : undefined }}
        >
          <SlidersHorizontal size={14} />
          Filters {hasFilters ? `(active)` : ''}
        </button>
        {hasFilters && (
          <button className="btn btn-ghost btn-sm" onClick={clearFilters}>
            Clear
          </button>
        )}
        {/* Sort */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <select
            className="form-select"
            style={{ padding: '0.5rem 2rem 0.5rem 0.75rem', fontSize: '0.875rem' }}
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
          >
            {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button
            className="btn btn-icon btn-ghost"
            onClick={() => setDescending((d) => !d)}
            title={descending ? 'Descending' : 'Ascending'}
          >
            {descending ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </div>

      {/* Filter row */}
      {showFilters && (
        <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
          <div className="filter-row">
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
                <option value="">All categories</option>
                {['harmful_unsafe_output','hallucination_misinformation','privacy_data_leakage','bias_discrimination','security_vulnerability_abuse','reliability_system_failure','copyright_ip_concern','other_unclassified'].map((c) => (
                  <option key={c} value={c}>{formatCategory(c)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Severity</label>
              <select className="form-select" value={severity} onChange={(e) => { setSeverity(e.target.value); setPage(1); }}>
                <option value="">All severities</option>
                {SEVERITY_OPTIONS.filter(Boolean).map((s) => <option key={s} value={s}>{formatLabel(s)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {STATUS_OPTIONS.filter(Boolean).map((s) => <option key={s} value={s}>{formatLabel(s)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Verification</label>
              <select className="form-select" value={verificationStatus} onChange={(e) => { setVerificationStatus(e.target.value); setPage(1); }}>
                <option value="">All verification states</option>
                {VERIFICATION_OPTIONS.filter(Boolean).map((s) => <option key={s} value={s}>{formatLabel(s)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Provider</label>
              <input className="form-input" placeholder="Filter by provider" value={provider} onChange={(e) => { setProvider(e.target.value); setPage(1); }} />
            </div>
            <div className="form-group">
              <label className="form-label">Model</label>
              <input className="form-input" placeholder="Filter by model name" value={modelName} onChange={(e) => { setModelName(e.target.value); setPage(1); }} />
            </div>
            <div className="form-group">
              <label className="form-label">From</label>
              <input type="date" className="form-input" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />
            </div>
            <div className="form-group">
              <label className="form-label">To</label>
              <input type="date" className="form-input" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />
            </div>
          </div>
        </div>
      )}

      {/* Results summary */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {loading ? 'Loading…' : `${total.toLocaleString()} incident${total !== 1 ? 's' : ''}`}
        </span>
      </div>

      {error && <ErrorState message={error} />}

      {!error && (
        <>
          {loading ? (
            <LoadingSkeleton rows={8} height={56} />
          ) : incidents.length === 0 ? (
            <EmptyState
              icon={<Search size={24} />}
              title="No incidents found"
              description={hasFilters ? 'Try adjusting your filters.' : 'No incidents have been reported yet.'}
              action={
                <button className="btn btn-primary btn-sm" onClick={() => navigate('/report')}>
                  Report Incident
                </button>
              }
            />
          ) : (
            <>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Title</th>
                      <th>Category</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Verification</th>
                      <th>Provider</th>
                      <th>Reported</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.map((inc) => (
                      <tr key={inc.incident_id} onClick={() => navigate(`/incidents/${inc.incident_id}`)}>
                        <td>
                          <span className="incident-id">{inc.incident_id}</span>
                          {inc.is_demo && <DemoBadge />}
                        </td>
                        <td style={{ maxWidth: 300 }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.875rem' }}>
                            {inc.title}
                          </div>
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{formatCategory(inc.category)}</td>
                        <td>
                          {inc.severity ? (
                            <span className={severityBadgeClass(inc.severity)}>{inc.severity}</span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span className={statusBadgeClass(inc.status)}>{formatLabel(inc.status)}</span>
                        </td>
                        <td>
                          <span className={verificationBadgeClass(inc.verification_status)}>
                            {formatLabel(inc.verification_status)}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{inc.provider ?? '—'}</td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {formatDate(inc.report_date)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </>
          )}
        </>
      )}
    </div>
  );
}
