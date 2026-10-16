import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Zap, AlertTriangle, Search } from 'lucide-react';
import api from '../api/client';
import type { Incident, AIAssessment } from '../api/client';
import { PageHeader, LoadingSkeleton } from '../components/ui';
import {
  formatCategory, formatDateTime,
  statusBadgeClass, verificationBadgeClass, displayTitle,
} from '../utils/format';

export default function TriagePage() {
  const location = useLocation();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string>(location.state?.incidentId ?? '');
  const [incident, setIncident] = useState<Incident | null>(null);
  const [assessments, setAssessments] = useState<AIAssessment[]>([]);
  const [loading, setLoading] = useState(false);
  const [triageLoading, setTriageLoading] = useState(false);
  const [triageError, setTriageError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [searchQ, setSearchQ] = useState('');

  // Review form
  const [reviewCategory, setReviewCategory] = useState('');
  const [reviewSeverity, setReviewSeverity] = useState('');
  const [reviewer, setReviewer] = useState('');
  const [justification, setJustification] = useState('');
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState('');
  const [reviewSuccess, setReviewSuccess] = useState('');

  // Load incident list
  useEffect(() => {
    setListLoading(true);
    api.incidents.list({ page_size: 50, sort_by: 'updated_at', descending: true })
      .then((r) => setIncidents(r.incidents))
      .catch(() => {})
      .finally(() => setListLoading(false));
  }, []);

  // Load incident + assessments when selection changes
  useEffect(() => {
    if (!selectedId) { setIncident(null); setAssessments([]); return; }
    setLoading(true);
    Promise.all([
      api.incidents.get(selectedId),
      api.incidents.assessments(selectedId),
    ]).then(([inc, asmt]) => {
      setIncident(inc);
      setAssessments(asmt);
      const latest = asmt[asmt.length - 1];
      if (latest) {
        setReviewCategory(latest.suggested_category);
        setReviewSeverity(latest.suggested_severity);
      }
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedId]);

  const filteredIncidents = incidents.filter((inc) =>
    !searchQ || inc.incident_id.includes(searchQ) || inc.title.toLowerCase().includes(searchQ.toLowerCase())
  );

  async function runTriage() {
    if (!selectedId) return;
    setTriageLoading(true);
    setTriageError(null);
    try {
      const asmt = await api.incidents.triage(selectedId);
      setAssessments((prev) => [...prev, asmt]);
      setReviewCategory(asmt.suggested_category);
      setReviewSeverity(asmt.suggested_severity);
    } catch (e: any) {
      setTriageError(e.detail ?? e.message ?? 'Triage failed');
    } finally {
      setTriageLoading(false);
    }
  }

  async function submitReview() {
    if (!selectedId || !reviewCategory || !reviewSeverity) return;
    setReviewError('');
    setReviewSuccess('');
    setReviewLoading(true);
    try {
      const updated = await api.incidents.reviewTriage(selectedId, {
        category: reviewCategory,
        severity: reviewSeverity,
        reviewer: reviewer || undefined,
        justification: justification || undefined,
      });
      setIncident(updated);
      setReviewSuccess('Human determination recorded successfully.');
    } catch (e: any) {
      setReviewError(e.detail ?? e.message ?? 'Review submission failed');
    } finally {
      setReviewLoading(false);
    }
  }

  const latestAssessment = assessments[assessments.length - 1] ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="AI Triage"
        title="AI Triage Workspace"
        description="Run AI assessment on incidents and record human determinations. AI suggestions are advisory; AI never auto-verifies."
      />

      <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
        <AlertTriangle size={16} />
        In demo mode, the deterministic keyword-based provider is used — no paid AI calls are made.
        AI triage advances verification from 'Reported' to 'AI Assessed' only.
        Human reviewers must record the final determination.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem' }}>
        {/* Incident selector */}
        <div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="search-bar">
                <Search size={14} className="search-icon" />
                <input
                  className="form-input"
                  style={{ paddingLeft: '2.25rem', padding: '0.5rem 0.75rem 0.5rem 2.25rem', fontSize: '0.8125rem' }}
                  placeholder="Search incidents…"
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                />
              </div>
            </div>
            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              {listLoading ? (
                <div style={{ padding: '1rem' }}><LoadingSkeleton rows={5} height={40} /></div>
              ) : filteredIncidents.length === 0 ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>No incidents found</div>
              ) : (
                filteredIncidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    onClick={() => setSelectedId(inc.incident_id)}
                    style={{
                      padding: '0.75rem 1rem',
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--border-subtle)',
                      background: selectedId === inc.incident_id ? 'var(--bg-elevated)' : 'transparent',
                      borderLeft: selectedId === inc.incident_id ? '2px solid var(--text-primary)' : '2px solid transparent',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', marginBottom: '0.25rem' }}>{inc.incident_id}</div>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{displayTitle(inc.title)}</div>
                    <div style={{ display: 'flex', gap: '0.375rem', marginTop: '0.375rem', flexWrap: 'wrap' }}>
                      <span className={statusBadgeClass(inc.status)} style={{ fontSize: '0.65rem', padding: '0.1rem 0.375rem' }}>{inc.status}</span>
                      <span className={verificationBadgeClass(inc.verification_status)} style={{ fontSize: '0.65rem', padding: '0.1rem 0.375rem' }}>{inc.verification_status}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Main triage panel */}
        <div>
          {!selectedId ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
              <Zap size={36} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Select an Incident</h4>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Choose an incident from the list to review or run AI triage.</p>
            </div>
          ) : loading ? (
            <LoadingSkeleton rows={6} height={60} />
          ) : incident ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Incident summary */}
              <div className="card">
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.875rem' }}>
                  <span className="incident-id">{incident.incident_id}</span>
                  <span className={statusBadgeClass(incident.status)}>{incident.status}</span>
                  <span className={verificationBadgeClass(incident.verification_status)}>{incident.verification_status}</span>
                  {incident.severity && <span className={severityBadgeClass(incident.severity)}>{incident.severity}</span>}
                </div>
                <h4 style={{ marginBottom: '0.5rem' }}>{displayTitle(incident.title)}</h4>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0 0 0.75rem 0', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {incident.description}
                </p>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={runTriage}
                  disabled={triageLoading}
                  style={{ gap: '0.5rem' }}
                >
                  <Zap size={14} />
                  {triageLoading ? 'Running assessment…' : `Run AI Triage ${assessments.length > 0 ? '(reassess)' : ''}`}
                </button>
                {triageError && <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>{triageError}</div>}
              </div>

              {/* Latest assessment */}
              {latestAssessment && (
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                    <h4>Latest Assessment</h4>
                    <span className="badge badge-violet">
                      {latestAssessment.provider_mode === 'demo' ? 'Automated Engine' : 'AI Provider'}
                    </span>
                    {assessments.length > 1 && (
                      <span className="badge badge-neutral">{assessments.length} assessments total</span>
                    )}
                  </div>

                  <div className="alert alert-info" style={{ marginBottom: '1rem', fontSize: '0.8rem' }}>
                    <AlertTriangle size={13} />
                    Advisory only. Suggestions below must be reviewed and accepted or overridden by a human reviewer before being applied.
                  </div>

                  <div className="grid-2" style={{ gap: '1rem', marginBottom: '1.25rem' }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>Suggested Category</div>
                      <span className="badge badge-neutral">{formatCategory(latestAssessment.suggested_category)}</span>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>Suggested Severity</div>
                      <span className={severityBadgeClass(latestAssessment.suggested_severity)}>{latestAssessment.suggested_severity}</span>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.25rem' }}>Risk Score</div>
                      <span style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{latestAssessment.risk_score}<span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/100</span></span>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.25rem' }}>Confidence</div>
                      <span style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{Math.round(latestAssessment.confidence * 100)}<span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>%</span></span>
                    </div>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.375rem' }}>Observed Concern</div>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>{latestAssessment.observed_failure_or_concern}</p>
                  </div>

                  {latestAssessment.missing_information.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.375rem' }}>Missing Information / Limitations</div>
                      <ul style={{ paddingLeft: '1.25rem', margin: 0 }}>
                        {latestAssessment.missing_information.map((item, i) => (
                          <li key={i} style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '1rem' }}>
                    {formatDateTime(latestAssessment.created_at)} · Model: {latestAssessment.model_name}{latestAssessment.model_version ? ` (${latestAssessment.model_version})` : ''} · {latestAssessment.provider_mode}
                  </div>
                </div>
              )}

              {/* Human review form */}
              {latestAssessment && (
                <div className="card">
                  <h4 style={{ marginBottom: '0.5rem' }}>Human Determination</h4>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
                    Accept the AI suggestion or override category/severity with a justification. This records your decision and advances the verification state to Human Reviewed.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                    <div className="grid-2">
                      <div className="form-group">
                        <label className="form-label required">Category Determination</label>
                        <select className="form-select" value={reviewCategory} onChange={(e) => setReviewCategory(e.target.value)}>
                          {['harmful_unsafe_output','hallucination_misinformation','privacy_data_leakage','bias_discrimination','security_vulnerability_abuse','reliability_system_failure','copyright_ip_concern','other_unclassified'].map((c) => (
                            <option key={c} value={c}>{formatCategory(c)}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label required">Severity Determination</label>
                        <select className="form-select" value={reviewSeverity} onChange={(e) => setReviewSeverity(e.target.value)}>
                          {['critical', 'high', 'medium', 'low'].map((s) => (
                            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Reviewer Name</label>
                      <input className="form-input" placeholder="Your name (not authenticated)" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label className="form-label" style={{ color: (reviewCategory !== latestAssessment.suggested_category || reviewSeverity !== latestAssessment.suggested_severity) ? 'var(--severity-critical)' : undefined }}>
                        Justification {(reviewCategory !== latestAssessment.suggested_category || reviewSeverity !== latestAssessment.suggested_severity) ? '(required — you overrode AI)' : '(optional if accepting AI suggestion)'}
                      </label>
                      <textarea className="form-textarea" placeholder="Explain your determination…" value={justification} onChange={(e) => setJustification(e.target.value)} rows={3} />
                    </div>
                    {reviewError && <div className="alert alert-error">{reviewError}</div>}
                    {reviewSuccess && <div className="alert alert-success">{reviewSuccess}</div>}
                    <button
                      className="btn btn-primary"
                      disabled={!reviewCategory || !reviewSeverity || reviewLoading}
                      onClick={submitReview}
                    >
                      {reviewLoading ? 'Recording…' : 'Record Human Determination'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function severityBadgeClass(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'badge badge-critical';
    case 'high': return 'badge badge-high';
    case 'medium': return 'badge badge-medium';
    case 'low': return 'badge badge-low';
    default: return 'badge badge-neutral';
  }
}
