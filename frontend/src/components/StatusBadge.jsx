const STATUS_LABELS = {
  pending: 'Pending',
  applied: 'Applied',
  rejected: 'Rejected',
  skipped: 'Skipped',
  in_progress: 'In Progress',
};

export default function StatusBadge({ status, label }) {
  const displayLabel = label || STATUS_LABELS[status] || status;
  return (
    <span className={`status-badge status-badge--${status}`}>{displayLabel}</span>
  );
}
