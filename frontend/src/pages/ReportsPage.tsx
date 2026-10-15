import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Download,
  FileText,
  FileSpreadsheet,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';
import api from '../api/client';
import type { Incident } from '../api/client';
import { PageHeader, LoadingSkeleton, ErrorState } from '../components/ui';

export default function ReportsPage() {
  const [searchParams] = useSearchParams();
  const preselectedId = searchParams.get('id');

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string>(preselectedId || '');
  const [redactReporter, setRedactReporter] = useState(false);
  const [previewContent, setPreviewContent] = useState<string>('');

  const [loadingIncidents, setLoadingIncidents] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [pdfGenerating, setPdfGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available incidents for dropdown
  useEffect(() => {
    api.incidents
      .list({ page_size: 100, sort_by: 'created_at', descending: true })
      .then((res) => {
        setIncidents(res.incidents);
        if (!selectedId && res.incidents.length > 0) {
          setSelectedId(res.incidents[0].incident_id);
        }
      })
      .catch((err) => setError(err.message || 'Failed to load incidents list.'))
      .finally(() => setLoadingIncidents(false));
  }, []);

  // Fetch report markdown whenever selectedId or redactReporter changes
  useEffect(() => {
    if (!selectedId) {
      setPreviewContent('');
      return;
    }
    let cancelled = false;
    setLoadingPreview(true);
    fetch(api.reports.markdownUrl(selectedId, redactReporter))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((text) => {
        if (!cancelled) setPreviewContent(text);
      })
      .catch((err) => {
        if (!cancelled) setError(`Failed to load report: ${err.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoadingPreview(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId, redactReporter]);

  const handleCopy = () => {
    if (!previewContent) return;
    navigator.clipboard.writeText(previewContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!selectedId) return;
    window.open(api.reports.markdownUrl(selectedId, redactReporter), '_blank');
  };

  const handleDownloadPdf = async () => {
    if (!selectedId) return;
    setPdfGenerating(true);
    try {
      const url = api.reports.pdfUrl(selectedId, redactReporter);
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server returned ${res.status}`);
      }
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `sentinel-${selectedId.toLowerCase()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      alert(`PDF Generation notice: ${err.message}`);
    } finally {
      setPdfGenerating(false);
    }
  };

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Compliance & Governance"
        title="Reports & Audit Exports"
        description="Generate formal, portable case summaries, markdown audits, executive PDFs, and tabular CSV registers."
      />

      {error && <ErrorState message={error} />}

      {/* Case Report Generation Section */}
      <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <FileText size={18} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>Incident Case Summary Report</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem', alignItems: 'end' }}>
          <div>
            <label className="form-label">Select Incident Record</label>
            {loadingIncidents ? (
              <LoadingSkeleton rows={1} height={40} />
            ) : (
              <select
                className="select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                style={{ width: '100%' }}
              >
                {incidents.map((inc) => (
                  <option key={inc.incident_id} value={inc.incident_id}>
                    {inc.incident_id} — {inc.title.slice(0, 50)} {inc.is_demo ? '(DEMO)' : ''}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
                fontSize: '0.875rem',
                color: 'var(--text-secondary)',
                userSelect: 'none',
                height: '42px',
              }}
            >
              <input
                type="checkbox"
                checked={redactReporter}
                onChange={(e) => setRedactReporter(e.target.checked)}
                style={{ width: '1rem', height: '1rem', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Redact reporter contact details in export</span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
          <button
            className="btn btn-primary"
            onClick={handleDownloadMarkdown}
            disabled={!selectedId}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Download size={15} />
            Download Markdown (.md)
          </button>

          <button
            className="btn btn-ghost"
            onClick={handleDownloadPdf}
            disabled={!selectedId || pdfGenerating}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', border: '1px solid var(--border-subtle)' }}
          >
            {pdfGenerating ? <RefreshCw size={15} className="spin" /> : <Download size={15} />}
            {pdfGenerating ? 'Generating PDF...' : 'Download PDF Report (.pdf)'}
          </button>

          <button
            className="btn btn-ghost"
            onClick={handleCopy}
            disabled={!previewContent}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto' }}
          >
            {copied ? <Check size={15} color="var(--color-verified)" /> : <Copy size={15} />}
            {copied ? 'Copied to Clipboard' : 'Copy Preview'}
          </button>
        </div>

        {/* Live Preview Box */}
        <div>
          <div className="eyebrow" style={{ marginBottom: '0.5rem' }}>Generated Report Document Preview</div>
          {loadingPreview ? (
            <LoadingSkeleton rows={6} height={36} />
          ) : (
            <textarea
              readOnly
              value={previewContent || 'Select an incident above to preview its report.'}
              style={{
                width: '100%',
                height: '340px',
                padding: '1rem',
                borderRadius: '8px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                lineHeight: 1.6,
                resize: 'vertical',
              }}
            />
          )}
        </div>
      </div>

      {/* Incident Register CSV Export Section */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <FileSpreadsheet size={18} color="var(--text-primary)" />
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>Incident Register CSV Export</h2>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', maxWidth: '680px', marginBottom: '1.25rem' }}>
          Tabular overview of recorded incidents. Formula characters are sanitized for spreadsheet safety.
          Includes IDs, severities, verification statuses, affected systems, and timeline timestamps.
        </p>

        <a
          href={api.reports.csvUrl()}
          download="sentinel-incident-register.csv"
          className="btn btn-primary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}
        >
          <Download size={15} />
          Download Full Incident Register (CSV)
        </a>
      </div>
    </div>
  );
}
