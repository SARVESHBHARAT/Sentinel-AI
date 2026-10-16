import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Shield, AlertTriangle,
  MessageSquare, ChevronDown, ChevronUp, Plus, Zap,
} from 'lucide-react';
import api from '../api/client';
import type { Incident, AIAssessment, ActivityResponse } from '../api/client';
import {
  LoadingSkeleton, ErrorState, Breadcrumb,
} from '../components/ui';
import {
  formatDate, formatDateTime, formatCategory, formatLabel, formatVerification,
  formatStatus, verificationBadgeClass, statusBadgeClass, displayTitle,
} from '../utils/format';

export default function IncidentDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [assessments, setAssessments] = useState<AIAssessment[]>([]);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'triage' | 'verification' | 'history'>('overview');

  // Verification controls
  const [verifyAction, setVerifyAction] = useState('');
  const [verifyReviewer, setVerifyReviewer] = useState('');
  const [verifyJustification, setVerifyJustification] = useState('');
  const [verifyError, setVerifyError] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

  // Status transition
  const [statusTarget, setStatusTarget] = useState('');
  const [statusActor, setStatusActor] = useState('');
  const [statusError, setStatusError] = useState('');
  const [statusLoading, setStatusLoading] = useState(false);

  // Note form
  const [noteBody, setNoteBody] = useState('');
  const [noteAuthor, setNoteAuthor] = useState('');
  const [noteLoading, setNoteLoading] = useState(false);
  const [noteError, setNoteError] = useState('');

  // Action form
  const [actionTitle, setActionTitle] = useState('');
  const [actionKind, setActionKind] = useState('corrective');
  const [actionOwner, setActionOwner] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  const load = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [inc, asmt, act] = await Promise.all([
        api.incidents.get(id),
        api.incidents.assessments(id),
        api.incidents.activity(id),
      ]);
      setIncident(inc);
      setAssessments(asmt);
      setActivity(act);
    } catch (e: any) {
      setError(e.detail ?? e.message ?? 'Failed to load incident');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  // ── Allowed status transitions ─────────────────────────────────────────────
  const ALLOWED_TRANSITIONS: Record<string, string[]> = {
    submitted: ['under_review'],
    under_review: ['action_required', 'resolved'],
    action_required: ['under_review', 'resolved'],
    resolved: ['closed', 'action_required'],
    closed: [],
  };

  const allowedStatuses = incident ? (ALLOWED_TRANSITIONS[incident.status] ?? []) : [];

  // ── Allowed verification actions ──────────────────────────────────────────
  function getAllowedVerificationActions(vs: string): string[] {
    switch (vs) {
      case 'reported': return ['mark_unverified'];
      case 'ai_assessed': return ['mark_unverified'];
      case 'human_reviewed': return ['verify', 'dispute', 'mark_unverified'];
      case 'verified': return ['dispute'];
      case 'disputed': return ['verify'];
      case 'unverified': return [];
      default: return [];
    }
  }

  const allowedVerifyActions = incident ? getAllowedVerificationActions(incident.verification_status) : [];

  async function handleStatusTransition() {
    if (!id || !statusTarget) return;
    setStatusError('');
    setStatusLoading(true);
    try {
      const updated = await api.incidents.transition(id, statusTarget, statusActor || undefined);
      setIncident(updated);
      setStatusTarget('');
      setStatusActor('');
      await load();
    } catch (e: any) {
      setStatusError(e.detail ?? e.message ?? 'Transition failed');
    } finally {
      setStatusLoading(false);
    }
  }

  async function handleVerification() {
    if (!id || !verifyAction) return;
    setVerifyError('');
    setVerifyLoading(true);
    try {
      const updated = await api.incidents.verify(id, verifyAction, verifyReviewer, verifyJustification);
      setIncident(updated);
      setVerifyAction('');
      setVerifyReviewer('');
      setVerifyJustification('');
      await load();
    } catch (e: any) {
      setVerifyError(e.detail ?? e.message ?? 'Verification failed');
    } finally {
      setVerifyLoading(false);
    }
  }

  async function handleAddNote() {
    if (!id || !noteBody.trim()) return;
    setNoteError('');
    setNoteLoading(true);
    try {
      await api.incidents.addNote(id, noteBody, noteAuthor || undefined);
      setNoteBody('');
      setNoteAuthor('');
      await load();
    } catch (e: any) {
      setNoteError(e.detail ?? e.message ?? 'Note submission failed');
    } finally {
      setNoteLoading(false);
    }
  }

  async function handleAddAction() {
    if (!id || !actionTitle.trim()) return;
    setActionError('');
    setActionLoading(true);
    try {
      await api.incidents.addAction(id, { title: actionTitle, action_kind: actionKind, owner: actionOwner || undefined });
      setActionTitle('');
      setActionOwner('');
      await load();
    } catch (e: any) {
      setActionError(e.detail ?? e.message ?? 'Action submission failed');
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div>
        <LoadingSkeleton rows={1} height={32} />
        <div style={{ marginTop: '2rem' }}>
          <LoadingSkeleton rows={6} height={64} />
        </div>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div>
        <Breadcrumb items={[{ label: 'Explorer', href: '/explorer' }, { label: 'Incident' }]} />
        <ErrorState message={error ?? 'Incident not found'} />
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: 'Explorer', href: '/explorer' }, { label: incident.incident_id }]} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.625rem', flexWrap: 'wrap' }}>
            <span className="incident-id" style={{ fontSize: '0.875rem' }}>{incident.incident_id}</span>
            <span className={statusBadgeClass(incident.status)}>{formatStatus(incident.status)}</span>
            <span className={verificationBadgeClass(incident.verification_status)}>{formatVerification(incident.verification_status)}</span>
          </div>
          <h1 style={{ fontSize: 'clamp(1.25rem, 2.5vw, 1.875rem)', fontWeight: 700, letterSpacing: '-0.025em', marginBottom: '0.375rem' }}>
            {displayTitle(incident.title)}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            <span>Reported: {formatDate(incident.report_date)}</span>
            {incident.provider && <span>Provider: {incident.provider}</span>}
            {incident.affected_model_name && <span>Model: {incident.affected_model_name}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/triage', { state: { incidentId: id } })}>
            <Zap size={14} /> AI Triage
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: '1.5rem' }}>
        {(['overview', 'triage', 'verification', 'history'] as const).map((tab) => (
          <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {tab === 'overview' ? 'Overview' : tab === 'triage' ? `AI Triage (${assessments.length})` : tab === 'verification' ? 'Verification' : 'History'}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ── */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Core details */}
          <div className="card">
            <h4 style={{ marginBottom: '1rem' }}>Incident Report</h4>
            <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '1.25rem' }}>
              {incident.description}
            </p>
            <div className="grid-3" style={{ gap: '1rem' }}>
              <InfoRow label="Category" value={formatCategory(incident.category)} />
              <InfoRow label="Category Source" value={formatLabel(incident.category_source)} />
              <InfoRow label="Severity" value={incident.severity ? formatLabel(incident.severity) : 'Not assessed'} />
              <InfoRow label="Occurrence Date" value={formatDate(incident.occurrence_date)} />
              <InfoRow label="Report Date" value={formatDate(incident.report_date)} />
              <InfoRow label="Assigned Reviewer" value={incident.assigned_reviewer ?? '—'} />
            </div>
          </div>

          {/* Affected system */}
          <div className="card">
            <h4 style={{ marginBottom: '1rem' }}>Affected AI System</h4>
            <div className="grid-2" style={{ gap: '1rem' }}>
              <InfoRow label="Provider" value={incident.provider ?? '—'} />
              <InfoRow label="Affected System" value={incident.affected_system ?? '—'} />
              <InfoRow label="Model Identifier" value={incident.affected_model_name ?? '—'} />
              <InfoRow label="Model Version" value={incident.affected_model_version ?? '—'} />
            </div>
          </div>

          {/* Impact */}
          {(incident.potential_impact || incident.affected_population) && (
            <div className="card">
              <h4 style={{ marginBottom: '1rem' }}>Impact & Stakeholders</h4>
              {incident.potential_impact && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.375rem' }}>Potential Impact</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>{incident.potential_impact}</p>
                </div>
              )}
              {incident.affected_population && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.375rem' }}>Affected Population</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>{incident.affected_population}</p>
                </div>
              )}
            </div>
          )}

          {/* Resolution */}
          {incident.resolution_summary && (
            <div className="card">
              <h4 style={{ marginBottom: '0.75rem' }}>Resolution Summary</h4>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>{incident.resolution_summary}</p>
            </div>
          )}

          {/* Status transition */}
          {allowedStatuses.length > 0 && (
            <div className="card-elevated">
              <h4 style={{ marginBottom: '1rem', fontSize: '0.875rem' }}>Transition Status</h4>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div className="form-group" style={{ minWidth: 180 }}>
                  <label className="form-label">New Status</label>
                  <select className="form-select" value={statusTarget} onChange={(e) => setStatusTarget(e.target.value)}>
                    <option value="">Select…</option>
                    {allowedStatuses.map((s) => <option key={s} value={s}>{formatStatus(s)}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ minWidth: 180 }}>
                  <label className="form-label">Actor (optional)</label>
                  <input className="form-input" placeholder="Your name" value={statusActor} onChange={(e) => setStatusActor(e.target.value)} />
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={!statusTarget || statusLoading}
                  onClick={handleStatusTransition}
                >
                  {statusLoading ? 'Transitioning…' : 'Apply'}
                </button>
              </div>
              {statusError && <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>{statusError}</div>}
            </div>
          )}

          {/* Notes section */}
          {activity && (
            <div className="card">
              <h4 style={{ marginBottom: '1rem' }}>
                <MessageSquare size={15} style={{ display: 'inline', marginRight: '0.5rem' }} />
                Reviewer Notes ({activity.reviewer_notes.length})
              </h4>
              {activity.reviewer_notes.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
                  {activity.reviewer_notes.map((note, i) => (
                    <div key={i} style={{ padding: '0.875rem', background: 'var(--bg-deep)', borderRadius: '8px', borderLeft: '2px solid var(--border-accent)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.375rem', fontFamily: 'var(--font-mono)' }}>
                        {note.author ?? 'Reviewer'} · {formatDateTime(note.created_at)}
                      </div>
                      <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{note.body}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1rem' }}>No notes recorded.</p>
              )}
              {/* Add note form */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">Add Note</label>
                    <textarea className="form-textarea" placeholder="Add a reviewer note…" value={noteBody} rows={3} onChange={(e) => setNoteBody(e.target.value)} />
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <div className="form-group" style={{ flex: 1, minWidth: 150 }}>
                      <label className="form-label">Author (optional)</label>
                      <input className="form-input" placeholder="Your name" value={noteAuthor} onChange={(e) => setNoteAuthor(e.target.value)} />
                    </div>
                    <button className="btn btn-secondary btn-sm" disabled={!noteBody.trim() || noteLoading} onClick={handleAddNote}>
                      {noteLoading ? 'Adding…' : <><Plus size={14} /> Add Note</>}
                    </button>
                  </div>
                  {noteError && <div className="alert alert-error">{noteError}</div>}
                </div>
              </div>
            </div>
          )}

          {/* Corrective actions */}
          {activity && (
            <div className="card">
              <h4 style={{ marginBottom: '1rem' }}>Corrective Actions ({activity.corrective_actions.length})</h4>
              {activity.corrective_actions.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', marginBottom: '1.25rem' }}>
                  {activity.corrective_actions.map((a, i) => (
                    <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.75rem', background: 'var(--bg-deep)', borderRadius: '8px' }}>
                      <span className={`badge ${a.status === 'completed' ? 'badge-verified' : a.status === 'cancelled' ? 'badge-neutral' : a.status === 'in_progress' ? 'badge-violet' : 'badge-info'}`}>{a.status}</span>
                      <span className={`badge ${a.action_kind === 'preventive' ? 'badge-info' : 'badge-neutral'}`}>{a.action_kind}</span>
                      <span style={{ flex: 1, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{a.title}</span>
                      {a.owner && <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{a.owner}</span>}
                    </div>
                  ))}
                </div>
              )}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                  <div className="form-group" style={{ flex: 2, minWidth: 200 }}>
                    <label className="form-label">Action Title</label>
                    <input className="form-input" placeholder="Describe the corrective action" value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} />
                  </div>
                  <div className="form-group" style={{ minWidth: 140 }}>
                    <label className="form-label">Kind</label>
                    <select className="form-select" value={actionKind} onChange={(e) => setActionKind(e.target.value)}>
                      <option value="corrective">Corrective</option>
                      <option value="preventive">Preventive</option>
                    </select>
                  </div>
                  <div className="form-group" style={{ minWidth: 140 }}>
                    <label className="form-label">Owner</label>
                    <input className="form-input" placeholder="Optional" value={actionOwner} onChange={(e) => setActionOwner(e.target.value)} />
                  </div>
                  <button className="btn btn-secondary btn-sm" disabled={!actionTitle.trim() || actionLoading} onClick={handleAddAction}>
                    {actionLoading ? 'Adding…' : <><Plus size={14} /> Add</>}
                  </button>
                </div>
                {actionError && <div className="alert alert-error" style={{ marginTop: '0.5rem' }}>{actionError}</div>}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TRIAGE TAB ── */}
      {activeTab === 'triage' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {assessments.length === 0 ? (
            <div className="card">
              <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>No AI assessments yet.</p>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/triage', { state: { incidentId: id } })}>
                <Zap size={14} /> Go to AI Triage
              </button>
            </div>
          ) : (
            assessments.map((a, i) => (
              <AssessmentCard key={i} assessment={a} index={i + 1} />
            ))
          )}
        </div>
      )}

      {/* ── VERIFICATION TAB ── */}
      {activeTab === 'verification' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <Shield size={18} color="var(--text-primary)" />
              <h4>Current Verification State</h4>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
              <span className={verificationBadgeClass(incident.verification_status)} style={{ fontSize: '0.9rem', padding: '0.375rem 0.875rem' }}>
                {formatVerification(incident.verification_status)}
              </span>
            </div>
            <div className="alert alert-info" style={{ marginBottom: '1.5rem', fontSize: '0.8125rem' }}>
              <AlertTriangle size={14} />
              AI assessments are advisory and never constitute verification. Only a human reviewer can verify or dispute an incident.
              Reviewer names are typed text — this application does not implement authentication.
            </div>

            {allowedVerifyActions.length > 0 ? (
              <div>
                <h5 style={{ marginBottom: '0.875rem', color: 'var(--text-secondary)' }}>Record a Determination</h5>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                  <div className="form-group">
                    <label className="form-label required">Action</label>
                    <select className="form-select" value={verifyAction} onChange={(e) => setVerifyAction(e.target.value)}>
                      <option value="">Select action…</option>
                      {allowedVerifyActions.includes('verify') && <option value="verify">Verify — findings are substantiated</option>}
                      {allowedVerifyActions.includes('dispute') && <option value="dispute">Dispute — findings are contested</option>}
                      {allowedVerifyActions.includes('mark_unverified') && <option value="mark_unverified">Mark Unverified — cannot be substantiated</option>}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label required">Reviewer Name</label>
                    <input className="form-input" placeholder="Your name (not authenticated)" value={verifyReviewer} onChange={(e) => setVerifyReviewer(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label required">Justification</label>
                    <textarea className="form-textarea" placeholder="Explain your determination and the evidence considered…" value={verifyJustification} onChange={(e) => setVerifyJustification(e.target.value)} rows={3} />
                  </div>
                  {verifyError && <div className="alert alert-error">{verifyError}</div>}
                  <button
                    className="btn btn-primary"
                    disabled={!verifyAction || !verifyReviewer.trim() || !verifyJustification.trim() || verifyLoading}
                    onClick={handleVerification}
                  >
                    {verifyLoading ? 'Processing…' : 'Record Determination'}
                  </button>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                No verification transitions available from the current state ({formatVerification(incident.verification_status)}).
              </p>
            )}
          </div>

          {/* Verification history */}
          {activity && (
            <div className="card">
              <h4 style={{ marginBottom: '1rem' }}>Verification History</h4>
              {activity.audit_events.filter((e) => e.event_type === 'verification_changed').length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No verification transitions recorded.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                  {activity.audit_events
                    .filter((e) => e.event_type === 'verification_changed')
                    .map((e, i) => (
                      <div key={i} style={{ display: 'flex', gap: '1rem', padding: '0.75rem', background: 'var(--bg-deep)', borderRadius: '8px', alignItems: 'center' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{e.details}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                            {e.actor ?? 'System'} · {formatDateTime(e.created_at)}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── HISTORY TAB ── */}
      {activeTab === 'history' && activity && (
        <div className="card">
          <h4 style={{ marginBottom: '1rem' }}>Audit Trail ({activity.audit_events.length} events)</h4>
          {activity.audit_events.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No audit events recorded.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {activity.audit_events.slice().reverse().map((e, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    gap: '1rem',
                    padding: '0.75rem 0',
                    borderBottom: '1px solid var(--border-subtle)',
                    alignItems: 'flex-start',
                  }}
                >
                  <div style={{ width: 120, flexShrink: 0, fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)', paddingTop: '0.1rem' }}>
                    {formatDateTime(e.created_at)}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-accent)', marginBottom: '0.1875rem' }}>{e.event_type}</div>
                    {e.details && <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{e.details}</div>}
                    {e.actor && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>Actor: {e.actor}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}

function AssessmentCard({ assessment, index }: { assessment: AIAssessment; index: number }) {
  const [expanded, setExpanded] = useState(index === 1);
  return (
    <div className="card">
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', justifyContent: 'space-between' }}
        onClick={() => setExpanded((e) => !e)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge badge-violet">#{index} {assessment.provider_mode === 'demo' ? 'Demo' : 'AI'} Assessment</span>
          <span className={severityBadgeClass(assessment.suggested_severity)}>{formatLabel(assessment.suggested_severity)}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{formatDateTime(assessment.created_at)}</span>
        </div>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </div>

      {expanded && (
        <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="alert alert-warning" style={{ fontSize: '0.8rem' }}>
            <AlertTriangle size={14} />
            AI assessments are advisory only. Human review is required before any determination is made.
            {assessment.provider_mode === 'demo' && ' This is a deterministic demo assessment — not a live AI result.'}
          </div>
          <InfoSection label="Concise Summary" content={assessment.concise_summary} />
          <InfoSection label="Observed Concern" content={assessment.observed_failure_or_concern} />
          <InfoSection label="Severity Explanation" content={assessment.severity_explanation} />
          <div className="grid-2">
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>Suggested Category</div>
              <span className="badge badge-neutral">{formatCategory(assessment.suggested_category)}</span>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>Risk Score</div>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{assessment.risk_score}<span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/100</span></span>
            </div>
          </div>
          {assessment.potential_harms.length > 0 && <BulletList label="Potential Harms" items={assessment.potential_harms} />}
          {assessment.missing_information.length > 0 && <BulletList label="Missing Information" items={assessment.missing_information} />}
          {assessment.immediate_containment_steps.length > 0 && <BulletList label="Containment Steps" items={assessment.immediate_containment_steps} />}
          {assessment.recommended_corrective_actions.length > 0 && <BulletList label="Recommended Actions" items={assessment.recommended_corrective_actions} />}
          {assessment.urgent_human_review_recommended && (
            <div className="alert alert-error" style={{ fontSize: '0.8125rem' }}>
              <AlertTriangle size={14} />
              Urgent human review recommended by this assessment.
            </div>
          )}
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Model: {assessment.model_name}{assessment.model_version ? ` (${assessment.model_version})` : ''} · Prompt: {assessment.prompt_version} · Mode: {assessment.provider_mode}
          </div>
        </div>
      )}
    </div>
  );
}

function InfoSection({ label, content }: { label: string; content: string }) {
  return (
    <div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.375rem' }}>{label}</div>
      <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{content}</p>
    </div>
  );
}

function BulletList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>{label}</div>
      <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {items.map((item, i) => <li key={i} style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{item}</li>)}
      </ul>
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
