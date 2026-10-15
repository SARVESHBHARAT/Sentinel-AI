import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Send, CheckCircle } from 'lucide-react';
import api from '../api/client';
import type { EnumsResponse } from '../api/client';
import { PageHeader, LoadingSkeleton } from '../components/ui';
import { formatCategory, formatLabel } from '../utils/format';

interface FormState {
  title: string;
  description: string;
  category: string;
  affected_system: string;
  provider: string;
  affected_model_name: string;
  affected_model_version: string;
  occurrence_date: string;
  report_date: string;
  severity: string;
  severity_source: string;
  potential_impact: string;
  affected_population: string;
  anonymous_report: boolean;
  reporter_name: string;
  reporter_contact: string;
  assigned_reviewer: string;
  evidence_references: string; // newline-separated
}

type FormErrors = Partial<Record<keyof FormState, string>>;

const EMPTY_FORM: FormState = {
  title: '',
  description: '',
  category: '',
  affected_system: '',
  provider: '',
  affected_model_name: '',
  affected_model_version: '',
  occurrence_date: '',
  report_date: new Date().toISOString().slice(0, 10),
  severity: '',
  severity_source: '',
  potential_impact: '',
  affected_population: '',
  anonymous_report: false,
  reporter_name: '',
  reporter_contact: '',
  assigned_reviewer: '',
  evidence_references: '',
};

export default function ReportIncidentPage() {
  const navigate = useNavigate();
  const [enums, setEnums] = useState<EnumsResponse | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    api.enums().then(setEnums).catch(() => {});
  }, []);

  function set(field: keyof FormState, value: string | boolean) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  }

  function validate(): boolean {
    const e: FormErrors = {};
    if (!form.title.trim()) e.title = 'Title is required';
    if (form.title.length > 300) e.title = 'Title must be ≤ 300 characters';
    if (!form.description.trim()) e.description = 'Description is required';
    if (form.description.length > 10000) e.description = 'Description must be ≤ 10,000 characters';
    if (!form.category) e.category = 'Category is required';
    if (form.occurrence_date && form.report_date && form.occurrence_date > form.report_date)
      e.occurrence_date = 'Occurrence date cannot be after report date';
    if (form.report_date > new Date().toISOString().slice(0, 10))
      e.report_date = 'Report date cannot be in the future';
    if ((form.severity && !form.severity_source) || (!form.severity && form.severity_source))
      e.severity = 'Severity and severity source must be supplied together';
    if (form.anonymous_report && (form.reporter_name || form.reporter_contact))
      e.reporter_name = 'Anonymous reports cannot include reporter details';
    if (form.affected_model_version && !/^[A-Za-z0-9][A-Za-z0-9._+-]*$/.test(form.affected_model_version))
      e.affected_model_version = 'Version must start with alphanumeric and contain only letters, digits, ., _, +, -';
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit() {
    setSubmitError(null);
    if (!validate()) return;

    const payload: Record<string, unknown> = {
      title: form.title,
      description: form.description,
      category: form.category,
      report_date: form.report_date,
      anonymous_report: form.anonymous_report,
    };
    if (form.affected_system) payload.affected_system = form.affected_system;
    if (form.provider) payload.provider = form.provider;
    if (form.affected_model_name) payload.affected_model_name = form.affected_model_name;
    if (form.affected_model_version) payload.affected_model_version = form.affected_model_version;
    if (form.occurrence_date) payload.occurrence_date = form.occurrence_date;
    if (form.severity) payload.severity = form.severity;
    if (form.severity_source) payload.severity_source = form.severity_source;
    if (form.potential_impact) payload.potential_impact = form.potential_impact;
    if (form.affected_population) payload.affected_population = form.affected_population;
    if (!form.anonymous_report) {
      if (form.reporter_name) payload.reporter_name = form.reporter_name;
      if (form.reporter_contact) payload.reporter_contact = form.reporter_contact;
    }
    if (form.assigned_reviewer) payload.assigned_reviewer = form.assigned_reviewer;
    const refs = form.evidence_references
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    if (refs.length) payload.evidence_references = refs;

    setSubmitting(true);
    try {
      const created = await api.incidents.create(payload);
      setSuccess(created.incident_id);
      setForm(EMPTY_FORM);
      setPreview(false);
    } catch (err: any) {
      setSubmitError(err.detail ?? err.message ?? 'Submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (!enums) {
    return (
      <div>
        <PageHeader eyebrow="Report" title="Report an Incident" />
        <LoadingSkeleton rows={6} height={48} />
      </div>
    );
  }

  if (success) {
    return (
      <div>
        <PageHeader eyebrow="Report" title="Incident Submitted" />
        <div className="card" style={{ maxWidth: 560, textAlign: 'center', margin: '0 auto', padding: '2.5rem' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(34,197,94,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4ade80', margin: '0 auto 1.25rem' }}>
            <CheckCircle size={28} />
          </div>
          <h3 style={{ marginBottom: '0.5rem' }}>Incident Reported</h3>
          <p style={{ marginBottom: '1.5rem' }}>
            Your report has been recorded with ID{' '}
            <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{success}</strong>.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => navigate(`/incidents/${success}`)}>
              View Incident
            </button>
            <button className="btn btn-secondary" onClick={() => setSuccess(null)}>
              Report Another
            </button>
            <button className="btn btn-ghost" onClick={() => navigate('/explorer')}>
              Explorer
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Report"
        title="Report an Incident"
        description="Document an AI system failure, harmful output, or governance concern. All fields are preserved with full audit history."
      />

      <div style={{ maxWidth: 760 }}>
        {/* Preview toggle */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <button
            className={`tab-btn ${!preview ? 'active' : ''}`}
            onClick={() => setPreview(false)}
          >
            Form
          </button>
          <button
            className={`tab-btn ${preview ? 'active' : ''}`}
            onClick={() => { if (validate()) setPreview(true); }}
          >
            Preview
          </button>
        </div>
        <div className="divider" style={{ marginTop: 0, marginBottom: '1.5rem' }} />

        {preview ? (
          <PreviewPanel form={form} onEdit={() => setPreview(false)} onSubmit={handleSubmit} submitting={submitting} submitError={submitError} />
        ) : (
          <FormPanel form={form} set={set} errors={errors} enums={enums} onPreview={() => { if (validate()) setPreview(true); }} />
        )}
      </div>
    </div>
  );
}

function Field({ label, required, error, hint, children }: {
  label: string; required?: boolean; error?: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div className="form-group">
      <label className={`form-label ${required ? 'required' : ''}`}>{label}</label>
      {children}
      {error && <div className="form-error">{error}</div>}
      {hint && !error && <div className="form-hint">{hint}</div>}
    </div>
  );
}

function FormPanel({
  form, set, errors, enums, onPreview,
}: {
  form: FormState;
  set: (k: keyof FormState, v: string | boolean) => void;
  errors: FormErrors;
  enums: EnumsResponse;
  onPreview: () => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Incident core */}
      <div className="card">
        <h4 style={{ marginBottom: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
          Incident Details
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Field label="Title" required error={errors.title}>
            <input
              className={`form-input ${errors.title ? 'error' : ''}`}
              placeholder="Brief, descriptive title for this incident"
              value={form.title}
              maxLength={300}
              onChange={(e) => set('title', e.target.value)}
            />
          </Field>
          <Field label="Description" required error={errors.description} hint="Describe the incident, its context, and what was observed. Up to 10,000 characters.">
            <textarea
              className={`form-textarea ${errors.description ? 'error' : ''}`}
              placeholder="Describe what happened, when you observed it, and what impact it had or may have..."
              value={form.description}
              maxLength={10000}
              rows={5}
              onChange={(e) => set('description', e.target.value)}
            />
          </Field>
          <div className="grid-2">
            <Field label="Category" required error={errors.category}>
              <select
                className={`form-select ${errors.category ? 'error' : ''}`}
                value={form.category}
                onChange={(e) => set('category', e.target.value)}
              >
                <option value="">Select category</option>
                {enums.categories.map((c) => (
                  <option key={c} value={c}>{formatCategory(c)}</option>
                ))}
              </select>
            </Field>
            <Field label="Report Date" required error={errors.report_date}>
              <input
                type="date"
                className={`form-input ${errors.report_date ? 'error' : ''}`}
                value={form.report_date}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => set('report_date', e.target.value)}
              />
            </Field>
          </div>
          <Field label="Occurrence Date" error={errors.occurrence_date} hint="When the incident actually occurred (if known). Must be on or before the report date.">
            <input
              type="date"
              className={`form-input ${errors.occurrence_date ? 'error' : ''}`}
              value={form.occurrence_date}
              max={form.report_date || new Date().toISOString().slice(0, 10)}
              onChange={(e) => set('occurrence_date', e.target.value)}
            />
          </Field>
        </div>
      </div>

      {/* Severity */}
      <div className="card">
        <h4 style={{ marginBottom: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
          Severity (Optional)
        </h4>
        <div className="grid-2">
          <Field label="Severity" error={errors.severity} hint="If provided, source must also be set.">
            <select className="form-select" value={form.severity} onChange={(e) => set('severity', e.target.value)}>
              <option value="">Not assessed</option>
              {enums.severities.map((s) => <option key={s} value={s}>{formatLabel(s)}</option>)}
            </select>
          </Field>
          <Field label="Severity Source">
            <select className="form-select" value={form.severity_source} onChange={(e) => set('severity_source', e.target.value)}>
              <option value="">— select if severity set —</option>
              <option value="human">Human assessment</option>
            </select>
          </Field>
        </div>
      </div>

      {/* Affected system */}
      <div className="card">
        <h4 style={{ marginBottom: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
          Affected AI System
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="grid-2">
            <Field label="Provider / Developer">
              <input className="form-input" placeholder="e.g. OpenAI, Google, Anthropic" value={form.provider} maxLength={200} onChange={(e) => set('provider', e.target.value)} />
            </Field>
            <Field label="Affected System">
              <input className="form-input" placeholder="e.g. ChatGPT, Gemini, Claude" value={form.affected_system} maxLength={200} onChange={(e) => set('affected_system', e.target.value)} />
            </Field>
          </div>
          <div className="grid-2">
            <Field label="Model Identifier" hint="Exact model name (e.g. gpt-4o, claude-3-5-sonnet)">
              <input className="form-input" placeholder="e.g. gpt-4o" value={form.affected_model_name} maxLength={200} onChange={(e) => set('affected_model_name', e.target.value)} />
            </Field>
            <Field label="Model Version" error={errors.affected_model_version} hint="Alphanumeric, ., _, +, - only">
              <input className={`form-input ${errors.affected_model_version ? 'error' : ''}`} placeholder="e.g. 2024-11-20" value={form.affected_model_version} maxLength={100} onChange={(e) => set('affected_model_version', e.target.value)} />
            </Field>
          </div>
        </div>
      </div>

      {/* Impact */}
      <div className="card">
        <h4 style={{ marginBottom: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
          Impact & Stakeholders
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Field label="Potential Impact" hint="Describe potential consequences, harms, or risks observed.">
            <textarea className="form-textarea" placeholder="Describe the actual or potential impact..." value={form.potential_impact} maxLength={5000} rows={3} onChange={(e) => set('potential_impact', e.target.value)} />
          </Field>
          <Field label="Affected Population" hint="Who is or may be affected (e.g. users of financial services AI, students, medical patients).">
            <input className="form-input" placeholder="Describe the affected group or population" value={form.affected_population} maxLength={2000} onChange={(e) => set('affected_population', e.target.value)} />
          </Field>
          <Field label="Evidence References" hint="One URL or reference per line (max 20).">
            <textarea className="form-textarea" placeholder="https://example.com/evidence&#10;https://another.com/link" value={form.evidence_references} rows={3} onChange={(e) => set('evidence_references', e.target.value)} />
          </Field>
        </div>
      </div>

      {/* Reporter */}
      <div className="card">
        <h4 style={{ marginBottom: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
          Reporter Information
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input
              type="checkbox"
              id="anonymous_report"
              checked={form.anonymous_report}
              onChange={(e) => set('anonymous_report', e.target.checked)}
              style={{ width: 16, height: 16, accentColor: 'var(--text-primary)', cursor: 'pointer' }}
            />
            <label htmlFor="anonymous_report" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              Submit anonymously
            </label>
          </div>
          {!form.anonymous_report && (
            <div className="grid-2">
              <Field label="Reporter Name" error={errors.reporter_name}>
                <input className="form-input" placeholder="Optional" value={form.reporter_name} maxLength={150} onChange={(e) => set('reporter_name', e.target.value)} />
              </Field>
              <Field label="Reporter Contact">
                <input className="form-input" placeholder="Email or contact (optional)" value={form.reporter_contact} maxLength={254} onChange={(e) => set('reporter_contact', e.target.value)} />
              </Field>
            </div>
          )}
          <Field label="Assign Reviewer (Optional)">
            <input className="form-input" placeholder="Name of reviewer to assign" value={form.assigned_reviewer} maxLength={150} onChange={(e) => set('assigned_reviewer', e.target.value)} />
          </Field>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', paddingBottom: '2rem' }}>
        <button className="btn btn-primary btn-lg" onClick={onPreview}>
          Review Before Submit <AlertTriangle size={16} />
        </button>
      </div>
    </div>
  );
}

function PreviewPanel({
  form, onEdit, onSubmit, submitting, submitError,
}: {
  form: FormState;
  onEdit: () => void;
  onSubmit: () => void;
  submitting: boolean;
  submitError: string | null;
}) {
  const rows: [string, string][] = [
    ['Title', form.title],
    ['Description', form.description],
    ['Category', formatCategory(form.category)],
    ['Report Date', form.report_date],
    ['Occurrence Date', form.occurrence_date || '—'],
    ['Severity', form.severity ? formatLabel(form.severity) : 'Not assessed'],
    ['Provider', form.provider || '—'],
    ['Affected System', form.affected_system || '—'],
    ['Model Identifier', form.affected_model_name || '—'],
    ['Model Version', form.affected_model_version || '—'],
    ['Potential Impact', form.potential_impact || '—'],
    ['Affected Population', form.affected_population || '—'],
    ['Anonymous', form.anonymous_report ? 'Yes' : 'No'],
    ...(form.anonymous_report ? [] : [
      ['Reporter Name', form.reporter_name || '—'] as [string, string],
      ['Reporter Contact', form.reporter_contact || '—'] as [string, string],
    ]),
    ['Assigned Reviewer', form.assigned_reviewer || '—'],
  ];

  return (
    <div>
      <div className="alert alert-info" style={{ marginBottom: '1.5rem' }}>
        <AlertTriangle size={16} />
        Review your report before submitting. Once submitted, the record is immutable — only status updates and notes can be added.
      </div>
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '0.625rem 0', width: '40%', fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', verticalAlign: 'top' }}>
                  {label}
                </td>
                <td style={{ padding: '0.625rem 0', fontSize: '0.9rem', color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                  {value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {submitError && <div className="alert alert-error" style={{ marginBottom: '1rem' }}>{submitError}</div>}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button className="btn btn-primary btn-lg" onClick={onSubmit} disabled={submitting}>
          {submitting ? 'Submitting…' : <><Send size={16} /> Submit Report</>}
        </button>
        <button className="btn btn-secondary" onClick={onEdit} disabled={submitting}>
          Edit
        </button>
      </div>
    </div>
  );
}
