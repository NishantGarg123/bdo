import { useEffect, useRef, useState } from 'react';
import SkillChips from '../../components/SkillChips';
import StatusBadge from '../../components/StatusBadge';
import { leadsAPI } from '../../services/api';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'analyzed', label: 'Analyzed' },
  { value: 'pending', label: 'Pending' },
  { value: 'applied', label: 'Applied' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'skipped', label: 'Skipped' },
  { value: 'in_progress', label: 'In Progress' },
];

const TIME_FILTER_OPTIONS = [
  { value: '24h', label: 'Last 24 Hours' },
  { value: '3d', label: 'Last 3 Days' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '14d', label: 'Last 14 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: 'all', label: 'All Time' },
];

const EMPTY_FORM = {
  title: '',
  description: '',
  url: '',
  search_keyword: '',
  budget: '',
  budget_min: '',
  budget_max: '',
  skills: '',
  job_type: '',
  posted_at: '',
  fetched_at: '',
  status: 'pending',
  skip_reason: '',
  total_proposals: 0,
};

function formatDateTime(dateString) {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatBudget(lead) {
  if (lead.budget) return lead.budget;
  if (lead.budget_min != null && lead.budget_max != null) {
    if (lead.budget_min === lead.budget_max) return `$${lead.budget_min}`;
    return `$${lead.budget_min} – $${lead.budget_max}`;
  }
  if (lead.budget_min != null) return `$${lead.budget_min}+`;
  if (lead.budget_max != null) return `Up to $${lead.budget_max}`;
  return '—';
}

function toDatetimeLocalValue(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function parseSkillsInput(value) {
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function leadToFormData(lead) {
  return {
    title: lead.title || '',
    description: lead.description || '',
    url: lead.url || '',
    search_keyword: lead.search_keyword || '',
    budget: lead.budget || '',
    budget_min: lead.budget_min ?? '',
    budget_max: lead.budget_max ?? '',
    skills: (lead.skills || []).join(', '),
    job_type: lead.job_type || '',
    posted_at: toDatetimeLocalValue(lead.posted_at),
    fetched_at: toDatetimeLocalValue(lead.fetched_at),
    status: lead.status || 'pending',
    skip_reason: lead.skip_reason || '',
    total_proposals: lead.total_proposals ?? 0,
  };
}

function formDataToPayload(formData) {
  const payload = {
    title: formData.title,
    description: formData.description || null,
    url: formData.url,
    search_keyword: formData.search_keyword || null,
    budget: formData.budget,
    skills: parseSkillsInput(formData.skills),
    job_type: formData.job_type,
    status: formData.status,
    skip_reason: formData.skip_reason,
    total_proposals: Number(formData.total_proposals) || 0,
  };

  if (formData.budget_min !== '') payload.budget_min = Number(formData.budget_min);
  if (formData.budget_max !== '') payload.budget_max = Number(formData.budget_max);
  if (formData.posted_at) payload.posted_at = new Date(formData.posted_at).toISOString();
  if (formData.fetched_at) payload.fetched_at = new Date(formData.fetched_at).toISOString();

  return payload;
}

export default function Leads({ fixedStatus, pageTitle = 'Leads', pageDescription = 'Manage and track your business development leads' }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('analyzed');
  const [selectedTimeFilter, setSelectedTimeFilter] = useState('24h');
  // A fixed-status route must not inherit filters from another route that
  // reuses this component (for example, Leads -> Applied Leads).
  const statusFilter = fixedStatus || selectedStatusFilter;
  const timeFilter = fixedStatus ? 'all' : selectedTimeFilter;
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [statusCounts, setStatusCounts] = useState({});
  const [applyingIds, setApplyingIds] = useState(new Set());
  const [statusMessage, setStatusMessage] = useState('');
  const [statusError, setStatusError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [viewingLead, setViewingLead] = useState(null);
  const [applyingLead, setApplyingLead] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [proposalDraft, setProposalDraft] = useState('');
  const [isEditingProposal, setIsEditingProposal] = useState(false);
  const [isSavingProposal, setIsSavingProposal] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [isDrawerExpanded, setIsDrawerExpanded] = useState(false);
  const [rejectingLead, setRejectingLead] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isSubmittingRejection, setIsSubmittingRejection] = useState(false);
  const [viewingRejectionReason, setViewingRejectionReason] = useState(null); // { title, reason }

  // Row selection & bulk refresh
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Keep latest filter values in refs so the fetch effect never has stale closures.
  const filtersRef = useRef({ search, statusFilter, timeFilter, page });
  useEffect(() => {
    filtersRef.current = { search, statusFilter, timeFilter, page };
  });

  // Stable fetch function — always reads current values from the ref.
  const fetchLeads = useRef(null);
  // A slow response for an old filter must never replace the most recent list.
  const latestRequestId = useRef(0);
  fetchLeads.current = async (targetPage) => {
    const { search: s, statusFilter: sf, timeFilter: tf } = filtersRef.current;
    const pg = targetPage ?? filtersRef.current.page;
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;
    setLoading(true);
    try {
      const params = { page: pg, time_filter: tf };
      if (s) params.search = s;
      if (sf) params.status = sf;
      const response = fixedStatus === 'applied'
        ? await leadsAPI.getApplied(params)
        : fixedStatus === 'rejected'
          ? await leadsAPI.getRejected({ search: s })
          : await leadsAPI.getAll(params);
      const data = response.data;
      // Filter changes may issue another request before this one returns.
      if (requestId !== latestRequestId.current) return;
      if (Array.isArray(data)) {
        setLeads(data);
        setTotalCount(data.length);
        setTotalPages(1);
        setStatusCounts({});
      } else {
        setLeads(data.results || []);
        setTotalCount(data.total ?? 0);
        setTotalPages(data.total_pages ?? 1);
        setStatusCounts(data.status_counts ?? {});
      }
    } catch (err) {
      if (requestId === latestRequestId.current) {
        console.error('Failed to load leads:', err);
      }
    } finally {
      if (requestId === latestRequestId.current) setLoading(false);
    }
  };

  // Convenience wrapper so call-sites don't reference the ref directly.
  const loadLeads = (targetPage) => fetchLeads.current(targetPage);

  // Tracks the last-fetched page so the page-change effect can skip no-op transitions.
  const prevPage = useRef(page);

  // Re-fetch (resetting to page 1) whenever any filter changes.
  useEffect(() => {
    setPage(1);
    prevPage.current = 1; // keep prevPage in sync so the page effect doesn't double-fetch
    setSelectedIds(new Set()); // clear selection on filter change
    fetchLeads.current(1);
  }, [search, statusFilter, timeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch when the user explicitly changes page (pagination buttons).
  useEffect(() => {
    if (prevPage.current === page) return; // skip on initial mount / filter resets
    prevPage.current = page;
    setSelectedIds(new Set()); // clear selection on page change
    fetchLeads.current(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!applyingLead) {
      setAnalysis(null);
      setProposalDraft('');
      setIsEditingProposal(false);
      return undefined;
    }

    let active = true;
    leadsAPI
      .getAnalysis(applyingLead.id)
      .then((response) => {
        if (active) {
          setAnalysis(response.data);
          setProposalDraft(response.data.proposal_draft || '');
          setIsEditingProposal(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load lead analysis:', err);
        if (active) setAnalysis(null);
      });

    return () => {
      active = false;
    };
  }, [applyingLead]);

  useEffect(() => {
    if (!applyingLead) return undefined;

    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setApplyingLead(null);
    };

    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [applyingLead]);

  const resetForm = () => {
    setFormData({
      ...EMPTY_FORM,
      fetched_at: toDatetimeLocalValue(new Date().toISOString()),
    });
    setEditingLead(null);
  };

  const openAddModal = () => {
    resetForm();
    setShowModal(true);
  };

  const openEditModal = (lead) => {
    setEditingLead(lead);
    setFormData(leadToFormData(lead));
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = formDataToPayload(formData);
      if (editingLead) {
        await leadsAPI.update(editingLead.id, payload);
      } else {
        await leadsAPI.create(payload);
      }
      setShowModal(false);
      resetForm();
      loadLeads(page);
    } catch (err) {
      console.error('Failed to save lead:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    try {
      await leadsAPI.delete(id);
      loadLeads(page);
    } catch (err) {
      console.error('Failed to delete lead:', err);
    }
  };

  /** Mark a lead as Applied via the quick-apply (✓) button */
  const handleQuickApply = async (lead) => {
    if (applyingIds.has(lead.id)) return;
    setStatusMessage('');
    setStatusError('');
    setApplyingIds((prev) => new Set(prev).add(lead.id));
    try {
      const response = await leadsAPI.apply(lead.id);
      const appliedLead = response.data;
      // Keep any open detail/apply panels synchronized before the list refreshes.
      setViewingLead((current) => (current?.id === lead.id ? appliedLead : current));
      setApplyingLead((current) => (current?.id === lead.id ? appliedLead : current));
      // Full reload: correctly removes the row from filtered views,
      // updates the list, and refreshes all status counts in one go.
      await fetchLeads.current(1);
      setPage(1);
      setStatusMessage(`Marked “${appliedLead.title}” as Applied.`);
    } catch (err) {
      console.error('Failed to apply lead:', err);
      setStatusError(
        err?.response?.data?.detail ||
        'Could not update this job. Please try again.'
      );
    } finally {
      setApplyingIds((prev) => {
        const next = new Set(prev);
        next.delete(lead.id);
        return next;
      });
    }
  };

  /** Mark a lead as Rejected with a reason */
  const handleReject = async () => {
    if (!rejectingLead || !rejectionReason.trim()) return;
    setIsSubmittingRejection(true);
    try {
      await leadsAPI.reject(rejectingLead.id, rejectionReason.trim());
      setRejectingLead(null);
      setRejectionReason('');
      loadLeads(page);
    } catch (err) {
      console.error('Failed to save rejection:', err);
    } finally {
      setIsSubmittingRejection(false);
    }
  };

  const startProposalEdit = () => {
    setProposalDraft(analysis?.proposal_draft || '');
    setSaveError('');
    setIsEditingProposal(true);
  };

  const cancelProposalEdit = () => {
    setProposalDraft(analysis?.proposal_draft || '');
    setSaveError('');
    setIsEditingProposal(false);
  };

  const saveProposal = async () => {
    if (!applyingLead) return;

    setIsSavingProposal(true);
    setSaveError('');
    try {
      const response = await leadsAPI.updateAnalysis(applyingLead.id, {
        proposal_draft: proposalDraft,
      });
      setAnalysis((currentAnalysis) => ({
        ...currentAnalysis,
        proposal_draft: response.data.proposal_draft,
      }));
      setProposalDraft(response.data.proposal_draft);
      setIsEditingProposal(false);
    } catch (err) {
      console.error('Failed to save proposal draft:', err);
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.proposal_draft?.[0] ||
        'Failed to save proposal. Please try again.';
      setSaveError(detail);
    } finally {
      setIsSavingProposal(false);
    }
  };

  /** Build label for status filter options, appending counts when available */
  const statusLabel = (opt) => {
    if (!opt.value) {
      // "All Statuses" — sum all counts
      const total = Object.values(statusCounts).reduce((a, b) => a + b, 0);
      return Object.keys(statusCounts).length > 0
        ? `All Statuses (${total})`
        : opt.label;
    }
    const count = statusCounts[opt.value];
    return count !== undefined ? `${opt.label} (${count})` : opt.label;
  };

  // ── Row selection helpers ──────────────────────────────────────────────────
  const allPageIds = leads.map((l) => l.id);
  const allSelected = allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id));
  const someSelected = allPageIds.some((id) => selectedIds.has(id));

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allPageIds));
    }
  };

  const toggleSelectRow = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  /** Refresh selected jobs — updates proposal, interviewing, invite_sent, hired */
  const handleRefresh = async () => {
    if (selectedIds.size === 0 || isRefreshing) return;
    setIsRefreshing(true);
    setStatusMessage('');
    setStatusError('');
    try {
      const ids = [...selectedIds];
      console.info('Requesting lead refresh for selected job IDs:', ids);
      const response = await leadsAPI.bulkRefresh(ids);
      const refreshed = response.data;
      // Reload from the normal list endpoint after the write completes. This
      // confirms the persisted values rather than relying on a stale local row.
      await fetchLeads.current(page);
      console.info('Lead refresh completed and list reloaded:', refreshed.map((lead) => lead.id));
      setStatusMessage(`Refreshed ${refreshed.length} job${refreshed.length !== 1 ? 's' : ''}.`);
    } catch (err) {
      console.error('Bulk refresh failed:', err);
      setStatusError(
        err?.response?.data?.detail || 'Refresh failed. Please try again.'
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  return (
    <div className="page leads-page">
      <div className="page-header page-header--row">
        <div>
          <h1>{pageTitle}</h1>
          <p>{pageDescription}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openAddModal}>
          + Add Lead
        </button>
      </div>

      {!fixedStatus && (
        <div className="status-filter-row" aria-label="Status filter">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`status-filter-option${statusFilter === opt.value ? ' status-filter-option--active' : ''}`}
              onClick={() => setSelectedStatusFilter(opt.value)}
              aria-pressed={statusFilter === opt.value}
            >
              {statusLabel(opt)}
            </button>
          ))}
        </div>
      )}

      <div className="toolbar">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by title, job type, budget, or skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {!fixedStatus && (
          <select
            value={timeFilter}
            onChange={(e) => setSelectedTimeFilter(e.target.value)}
            className="filter-select toolbar-time-filter"
            aria-label="Time range filter"
          >
            {TIME_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Summary row */}
      <div className="leads-summary">
        <span className="leads-summary__count">
          {loading ? 'Loading…' : `${totalCount} job${totalCount !== 1 ? 's' : ''} found`}
        </span>
        {!loading && totalPages > 1 && (
          <span className="leads-summary__page">
            Page {page} of {totalPages}
          </span>
        )}
      </div>
      {statusMessage && <div className="alert alert-success" role="status">{statusMessage}</div>}
      {statusError && <div className="alert alert-error" role="alert">{statusError}</div>}

      {/* Refresh toolbar — shown above the table */}
      <div className="refresh-toolbar">
        <button
          type="button"
          className="btn btn-secondary btn-refresh"
          disabled={selectedIds.size === 0 || isRefreshing}
          onClick={handleRefresh}
          title={selectedIds.size === 0 ? 'Select rows to refresh' : `Refresh ${selectedIds.size} selected job${selectedIds.size !== 1 ? 's' : ''}`}
        >
          {isRefreshing ? (
            <><span className="btn-refresh-spinner" aria-hidden="true" />Refreshing…</>
          ) : (
            <>
              <span aria-hidden="true">↻</span>
              {selectedIds.size > 0
                ? `Refresh (${selectedIds.size})`
                : 'Refresh'}
            </>
          )}
        </button>
      </div>

      <div className="table-card">
        {loading ? (
          <div className="page-loading">Loading leads...</div>
        ) : leads.length === 0 ? (
          <div className="empty-state">
            <p>No leads found.</p>
            <button type="button" className="btn btn-primary" onClick={openAddModal}>
              Add your first lead
            </button>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table data-table--wide">
              <thead>
                <tr>
                  {/* Checkbox — Select All */}
                  <th className="col-checkbox">
                    <input
                      type="checkbox"
                      className="row-checkbox"
                      checked={allSelected}
                      ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                      onChange={toggleSelectAll}
                      aria-label="Select all rows on this page"
                    />
                  </th>
                  {fixedStatus !== 'applied' && fixedStatus !== 'rejected' && <th>Actions</th>}
                  <th>Title</th>
                  <th>URL</th>
                  <th>Search Keyword</th>
                  <th>Budget</th>
                  <th>Job Type</th>
                  <th>Interviewing</th>
                  <th>Invite Sent</th>
                  <th>Hired</th>
                  <th>Proposals</th>
                  <th>Status</th>
                  {!fixedStatus && statusFilter === 'skipped' && <th>Skip Reason</th>}
                  <th>Posted At</th>
                  <th>Fetched At</th>
                  {fixedStatus === 'rejected' && <th>Reason</th>}
                  <th>Apply</th>
                  <th>View</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className={selectedIds.has(lead.id) ? 'row-selected' : ''}
                  >
                    {/* Per-row checkbox */}
                    <td className="col-checkbox">
                      <input
                        type="checkbox"
                        className="row-checkbox"
                        checked={selectedIds.has(lead.id)}
                        onChange={() => toggleSelectRow(lead.id)}
                        aria-label={`Select row for ${lead.title}`}
                      />
                    </td>
                    {fixedStatus !== 'applied' && fixedStatus !== 'rejected' && (
                      <td>
                        <div className="action-buttons">
                          {/* Quick-apply (✓) button */}
                          <button
                            type="button"
                            className={`btn btn-sm btn-apply-check${lead.status === 'applied' ? ' btn-apply-check--done' : ''}`}
                            title={lead.status === 'applied' ? 'Already applied' : 'Mark as Applied'}
                            disabled={lead.status === 'applied' || applyingIds.has(lead.id)}
                            onClick={() => handleQuickApply(lead)}
                            aria-label="Mark as Applied"
                          >
                            {applyingIds.has(lead.id) ? '…' : '✓'}
                          </button>
                          {/* Mark as Rejected (×) button */}
                          <button
                            type="button"
                            className="btn btn-sm btn-reject-check"
                            title="Mark as Rejected"
                            onClick={() => { setRejectingLead(lead); setRejectionReason(''); }}
                            aria-label="Mark as Rejected"
                            disabled={isSubmittingRejection && rejectingLead?.id === lead.id}
                          >
                            {isSubmittingRejection && rejectingLead?.id === lead.id ? '…' : '×'}
                          </button>
                          {selectedIds.size === 1 && selectedIds.has(lead.id) && (
                            <button
                              type="button"
                              className="btn btn-sm btn-row-refresh"
                              title="Refresh this selected job"
                              aria-label="Refresh this selected job"
                              disabled={isRefreshing}
                              onClick={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                handleRefresh();
                              }}
                            >
                              {isRefreshing ? <span className="btn-refresh-spinner" aria-hidden="true" /> : '↻'}
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                    <td className="cell-bold cell-title">{lead.title}</td>
                    <td>
                      {lead.url ? (
                        <a
                          href={lead.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="link-external"
                        >
                          View
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{lead.search_keyword || 'NA'}</td>
                    <td>{formatBudget(lead)}</td>
                    <td>{lead.job_type || '—'}</td>
                    {/* Tracking columns */}
                    <td className="cell-tracking">
                      {lead.interviewing && Number(lead.interview_count) > 0
                        ? <span className="tracking-badge-with-count">
                            <span className="tracking-badge tracking-badge--yes">Yes</span>
                            <sup className="tracking-count">{lead.interview_count}</sup>
                          </span>
                        : <span className="tracking-badge tracking-badge--no">No</span>}
                    </td>
                    <td className="cell-tracking">
                      {lead.invite_sent ?? 0}
                    </td>
                    <td className="cell-tracking">
                      {lead.hired
                        ? <span className="tracking-badge tracking-badge--yes">Yes</span>
                        : <span className="tracking-badge tracking-badge--no">No</span>}
                    </td>
                    <td className="cell-proposals">{lead.total_proposals ?? 0}</td>
                    <td>
                      <StatusBadge status={lead.status} label={lead.status_display} />
                    </td>
                    {!fixedStatus && statusFilter === 'skipped' && (
                      <td className="cell-muted">{lead.skip_reason || '—'}</td>
                    )}
                    <td className="cell-date">{formatDateTime(lead.posted_at)}</td>
                    <td className="cell-date">{formatDateTime(lead.fetched_at)}</td>
                    {fixedStatus === 'rejected' && (
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          onClick={() => setViewingRejectionReason({ title: lead.title, reason: lead.rejection_reason || 'No reason recorded.' })}
                        >
                          Reason
                        </button>
                      </td>
                    )}
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        disabled={lead.status !== 'analyzed'}
                        onClick={() => setApplyingLead(lead)}
                      >
                        Apply
                      </button>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        onClick={() => setViewingLead(lead)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination controls */}
      {!loading && totalPages > 1 && (
        <div className="pagination">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!canGoPrev}
            onClick={() => setPage((p) => p - 1)}
          >
            ← Previous
          </button>
          <span className="pagination__info">
            Page {page} of {totalPages} &nbsp;·&nbsp; {totalCount} total
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!canGoNext}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
      {/* Rejection reason popup (Rejected Leads page) */}
      {viewingRejectionReason && (
        <div className="modal-overlay" onClick={() => setViewingRejectionReason(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Rejection Reason</h2>
              <button type="button" className="modal-close" onClick={() => setViewingRejectionReason(null)}>
                ×
              </button>
            </div>
            <div className="modal-form">
              <p style={{ marginBottom: '0.5rem', fontWeight: 600 }}>{viewingRejectionReason.title}</p>
              <p style={{ color: 'var(--color-text-muted, #666)', whiteSpace: 'pre-wrap' }}>
                {viewingRejectionReason.reason}
              </p>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setViewingRejectionReason(null)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingLead ? 'Edit Lead' : 'Add Lead'}</h2>
              <button type="button" className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group form-group--full">
                  <label>Title *</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group form-group--full">
                  <label>Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Job description..."
                    rows={4}
                  />
                </div>
                <div className="form-group form-group--full">
                  <label>URL</label>
                  <input
                    type="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://"
                  />
                </div>
                <div className="form-group form-group--full">
                  <label>Search Keyword</label>
                  <input
                    type="text"
                    value={formData.search_keyword}
                    onChange={(e) => setFormData({ ...formData, search_keyword: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Budget (display)</label>
                  <input
                    type="text"
                    value={formData.budget}
                    onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                    placeholder="$5,000 - $8,000"
                  />
                </div>
                <div className="form-group">
                  <label>Job Type</label>
                  <input
                    type="text"
                    value={formData.job_type}
                    onChange={(e) => setFormData({ ...formData, job_type: e.target.value })}
                    placeholder="Fixed Price, Hourly..."
                  />
                </div>
                <div className="form-group">
                  <label>Budget Min</label>
                  <input
                    type="number"
                    value={formData.budget_min}
                    onChange={(e) => setFormData({ ...formData, budget_min: e.target.value })}
                    min="0"
                    step="0.01"
                  />
                </div>
                <div className="form-group">
                  <label>Budget Max</label>
                  <input
                    type="number"
                    value={formData.budget_max}
                    onChange={(e) => setFormData({ ...formData, budget_max: e.target.value })}
                    min="0"
                    step="0.01"
                  />
                </div>
                <div className="form-group form-group--full">
                  <label>Skills (comma-separated)</label>
                  <input
                    type="text"
                    value={formData.skills}
                    onChange={(e) => setFormData({ ...formData, skills: e.target.value })}
                    placeholder="React, Django, PostgreSQL"
                  />
                </div>
                <div className="form-group">
                  <label>Posted At</label>
                  <input
                    type="datetime-local"
                    value={formData.posted_at}
                    onChange={(e) => setFormData({ ...formData, posted_at: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Fetched At *</label>
                  <input
                    type="datetime-local"
                    value={formData.fetched_at}
                    onChange={(e) => setFormData({ ...formData, fetched_at: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    {STATUS_OPTIONS.filter((o) => o.value).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Total Proposals</label>
                  <input
                    type="number"
                    value={formData.total_proposals}
                    onChange={(e) =>
                      setFormData({ ...formData, total_proposals: e.target.value })
                    }
                    min="0"
                  />
                </div>
                <div className="form-group form-group--full">
                  <label>Skip Reason</label>
                  <input
                    type="text"
                    value={formData.skip_reason}
                    onChange={(e) => setFormData({ ...formData, skip_reason: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingLead ? 'Save Changes' : 'Add Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rejection reason modal */}
      {rejectingLead && (
        <div className="modal-overlay" onClick={() => setRejectingLead(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Mark as Rejected</h2>
              <button type="button" className="modal-close" onClick={() => setRejectingLead(null)}>
                ×
              </button>
            </div>
            <div className="modal-form">
              <p style={{ marginBottom: '0.75rem', color: 'var(--text-secondary, #666)' }}>
                Enter a reason for rejecting <strong>{rejectingLead.title}</strong>.
              </p>
              <div className="form-group form-group--full">
                <label htmlFor="rejection-reason-input">Rejection Reason *</label>
                <textarea
                  id="rejection-reason-input"
                  rows={4}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Budget too low, skills mismatch…"
                  disabled={isSubmittingRejection}
                  autoFocus
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setRejectingLead(null)}
                  disabled={isSubmittingRejection}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleReject}
                  disabled={!rejectionReason.trim() || isSubmittingRejection}
                >
                  {isSubmittingRejection ? 'Saving…' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {applyingLead && (
        <div className="apply-drawer-overlay" onClick={() => setApplyingLead(null)}>
          <aside
            className={`apply-drawer${isDrawerExpanded ? ' expanded' : ''}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="apply-drawer-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h2 id="apply-drawer-title">Apply</h2>
              <div className="drawer-header-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsDrawerExpanded((value) => !value)}
                >
                  {isDrawerExpanded ? 'Collapse' : 'Expand'}
                </button>
                <button type="button" className="modal-close" onClick={() => setApplyingLead(null)}>
                  ×
                </button>
              </div>
            </div>
            <div className="view-details">
              <div className="analysis-score" aria-label={`Score: ${analysis?.score ?? 'unavailable'}`}>
                Score <strong>{analysis?.score ?? '—'}</strong>
              </div>
              <div className="detail-row detail-row--block">
                <span className="detail-label">Job</span>
                <strong>{applyingLead.title}</strong>
              </div>
              <div className="detail-row detail-row--block">
                <span className="detail-label">Description</span>
                <p className="job-description">
                  {applyingLead.description || 'No job description available.'}
                </p>
                {applyingLead.url && (
                  <a href={applyingLead.url} target="_blank" rel="noopener noreferrer">
                    {applyingLead.url}
                  </a>
                )}
              </div>
            </div>
            <div className="view-details">
              <div className="detail-row detail-row--block">
                <span className="detail-label">Analysis</span>
                <span className="analysis-detail">
                  <strong>Score Reasoning</strong>
                  {analysis?.score_reasoning || '—'}
                </span>
                <span className="analysis-detail">
                  <strong>Tech Stack</strong>
                  {analysis?.tech_stack || '—'}
                </span>
              </div>
            </div>
            {/* <div className="modal-actions">
              <button type="button" className="btn btn-secondary">
                Generate Proposal
              </button>
            </div> */}
            <div className="view-details">
              <div className="detail-row detail-row--block">
                <span className="detail-label">Proposal</span>
                {isEditingProposal ? (
                  <textarea
                    className="proposal-draft-input"
                    value={proposalDraft}
                    onChange={(e) => setProposalDraft(e.target.value)}
                    aria-label="Proposal draft"
                    rows={12}
                    disabled={isSavingProposal}
                  />
                ) : (
                  <p className="proposal-draft-display">{analysis?.proposal_draft || 'No proposal draft available.'}</p>
                )}
              </div>
              <div className="modal-actions proposal-actions">
                {isEditingProposal ? (
                  <>
                    {saveError && (
                      <span className="proposal-save-error" role="alert">
                        {saveError}
                      </span>
                    )}
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={cancelProposalEdit}
                      disabled={isSavingProposal}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={saveProposal}
                      disabled={isSavingProposal}
                    >
                      {isSavingProposal ? 'Saving...' : 'Save'}
                    </button>
                  </>
                ) : (
                  <button type="button" className="btn btn-secondary" onClick={startProposalEdit}>
                    Edit
                  </button>
                )}
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" disabled>
                Apply
              </button>
            </div>
          </aside>
        </div>
      )}

      {viewingLead && (
        <div className="modal-overlay" onClick={() => setViewingLead(null)}>
          <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{viewingLead.title}</h2>
              <button type="button" className="modal-close" onClick={() => setViewingLead(null)}>
                ×
              </button>
            </div>
            <div className="view-details">
              <div className="detail-row">
                <span className="detail-label">URL</span>
                <span>
                  {viewingLead.url ? (
                    <a href={viewingLead.url} target="_blank" rel="noopener noreferrer">
                      {viewingLead.url}
                    </a>
                  ) : (
                    '—'
                  )}
                </span>
              </div>
              {viewingLead.description && (
                <div className="detail-row detail-row--block">
                  <span className="detail-label">Description</span>
                  <span>{viewingLead.description}</span>
                </div>
              )}
              <div className="detail-row">
                <span className="detail-label">Budget</span>
                <span>{formatBudget(viewingLead)}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Job Type</span>
                <span>{viewingLead.job_type || '—'}</span>
              </div>
              <div className="detail-row detail-row--block">
                <span className="detail-label">Skills</span>
                <SkillChips skills={viewingLead.skills} />
              </div>
              <div className="detail-row">
                <span className="detail-label">Posted At</span>
                <span>{formatDateTime(viewingLead.posted_at)}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Fetched At</span>
                <span>{formatDateTime(viewingLead.fetched_at)}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Status</span>
                <StatusBadge status={viewingLead.status} label={viewingLead.status_display} />
              </div>
              <div className="detail-row">
                <span className="detail-label">Total Proposals</span>
                <span>{viewingLead.total_proposals ?? 0}</span>
              </div>
              {viewingLead.skip_reason && (
                <div className="detail-row">
                  <span className="detail-label">Skip Reason</span>
                  <span>{viewingLead.skip_reason}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
