/**
 * Shared utility functions for the Sentinel AI frontend.
 */

// ─── Label formatters ─────────────────────────────────────────────────────────

export function formatLabel(value: string | null | undefined): string {
  if (!value) return 'Unknown';
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatCategory(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    harmful_unsafe_output: 'Harmful Output',
    hallucination_misinformation: 'Hallucination / Misinformation',
    privacy_data_leakage: 'Privacy / Data Leakage',
    bias_discrimination: 'Bias / Discrimination',
    security_vulnerability_abuse: 'Security Vulnerability',
    reliability_system_failure: 'Reliability Failure',
    copyright_ip_concern: 'Copyright / IP Concern',
    other_unclassified: 'Other / Unclassified',
  };
  return labels[value ?? ''] ?? formatLabel(value);
}

export function formatStatus(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    submitted: 'Submitted',
    under_review: 'Under Review',
    action_required: 'Action Required',
    resolved: 'Resolved',
    closed: 'Closed',
  };
  return labels[value ?? ''] ?? formatLabel(value);
}

export function formatVerification(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    reported: 'Reported',
    ai_assessed: 'AI Assessed',
    human_reviewed: 'Human Reviewed',
    verified: 'Verified',
    disputed: 'Disputed',
    unverified: 'Unverified',
  };
  return labels[value ?? ''] ?? formatLabel(value);
}

export function formatSeverity(value: string | null | undefined): string {
  if (!value) return 'Not Assessed';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

// ─── CSS class helpers ────────────────────────────────────────────────────────

export function severityBadgeClass(severity: string | null): string {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'badge badge-critical';
    case 'high': return 'badge badge-high';
    case 'medium': return 'badge badge-medium';
    case 'low': return 'badge badge-low';
    default: return 'badge badge-neutral';
  }
}

export function verificationBadgeClass(status: string | null): string {
  switch (status?.toLowerCase()) {
    case 'verified': return 'badge badge-verified';
    case 'disputed': return 'badge badge-disputed';
    case 'ai_assessed': return 'badge badge-violet';
    case 'human_reviewed': return 'badge badge-info';
    case 'reported': return 'badge badge-neutral';
    case 'unverified': return 'badge badge-neutral';
    default: return 'badge badge-neutral';
  }
}

export function statusBadgeClass(status: string | null): string {
  switch (status?.toLowerCase()) {
    case 'submitted': return 'badge badge-info';
    case 'under_review': return 'badge badge-violet';
    case 'action_required': return 'badge badge-high';
    case 'resolved': return 'badge badge-low';
    case 'closed': return 'badge badge-neutral';
    default: return 'badge badge-neutral';
  }
}

// ─── Date formatters ──────────────────────────────────────────────────────────

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    const diff = Date.now() - new Date(value).getTime();
    const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
    if (diff < 60_000) return 'just now';
    if (diff < 3_600_000) return rtf.format(-Math.floor(diff / 60_000), 'minute');
    if (diff < 86_400_000) return rtf.format(-Math.floor(diff / 3_600_000), 'hour');
    if (diff < 7 * 86_400_000) return rtf.format(-Math.floor(diff / 86_400_000), 'day');
    return formatDate(value);
  } catch {
    return value;
  }
}

// ─── Title display helpers ────────────────────────────────────────────────────

/**
 * Strips the `[DEMO]` prefix from incident titles for cleaner display.
 * The underlying data retains the prefix — this is presentation-only.
 */
export function displayTitle(title: string): string {
  return title.replace(/^\[DEMO\]\s*/i, '');
}

// ─── Misc ─────────────────────────────────────────────────────────────────────

export function truncate(text: string, maxLen = 80): string {
  return text.length > maxLen ? text.slice(0, maxLen - 1) + '…' : text;
}

export function classNames(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
