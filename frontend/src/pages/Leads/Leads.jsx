import { useCallback, useEffect, useState } from 'react';
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

const EMPTY_FORM = {
  title: '',
  url: '',
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
    url: lead.url || '',
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
    url: formData.url,
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

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('analyzed');
  const [showModal, setShowModal] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [viewingLead, setViewingLead] = useState(null);
  const [applyingLead, setApplyingLead] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const response = await leadsAPI.getAll(params);
      setLeads(response.data);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  useEffect(() => {
    if (!applyingLead) {
      setAnalysis(null);
      return undefined;
    }

    let active = true;
    leadsAPI
      .getAnalysis(applyingLead.id)
      .then((response) => {
        if (active) setAnalysis(response.data);
      })
      .catch((err) => {
        console.error('Failed to load lead analysis:', err);
        if (active) setAnalysis(null);
      });

    return () => {
      active = false;
    };
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
      loadLeads();
    } catch (err) {
      console.error('Failed to save lead:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    try {
      await leadsAPI.delete(id);
      loadLeads();
    } catch (err) {
      console.error('Failed to delete lead:', err);
    }
  };

  return (
    <div className="page leads-page">
      <div className="page-header page-header--row">
        <div>
          <h1>Leads</h1>
          <p>Manage and track your business development leads</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openAddModal}>
          + Add Lead
        </button>
      </div>

      <div className="toolbar">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by title, job type, budget, or skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filters-placeholder">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
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
                  <th>Title</th>
                  <th>URL</th>
                  <th>Budget</th>
                  <th>Skills</th>
                  <th>Job Type</th>
                  <th>Posted At</th>
                  <th>Fetched At</th>
                  <th>Status</th>
                  <th>Skip Reason</th>
                  <th>Proposals</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id}>
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
                    <td>{formatBudget(lead)}</td>
                    <td className="cell-skills">
                      <SkillChips skills={lead.skills} />
                    </td>
                    <td>{lead.job_type || '—'}</td>
                    <td className="cell-date">{formatDateTime(lead.posted_at)}</td>
                    <td className="cell-date">{formatDateTime(lead.fetched_at)}</td>
                    <td>
                      <StatusBadge status={lead.status} label={lead.status_display} />
                    </td>
                    <td className="cell-muted">{lead.skip_reason || '—'}</td>
                    <td>{lead.total_proposals ?? 0}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          disabled={lead.status !== 'analyzed'}
                          onClick={() => setApplyingLead(lead)}
                        >
                          Apply
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          onClick={() => setViewingLead(lead)}
                        >
                          View
                        </button>
                        {/* <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          onClick={() => openEditModal(lead)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger-ghost"
                          onClick={() => handleDelete(lead.id)}
                        >
                          Delete
                        </button> */}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
                  <label>URL</label>
                  <input
                    type="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://"
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

      {applyingLead && (
        <div className="modal-overlay" onClick={() => setApplyingLead(null)}>
          <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Apply</h2>
              <button type="button" className="modal-close" onClick={() => setApplyingLead(null)}>
                Ã—
              </button>
            </div>
            <div className="view-details">
              <div className="analysis-score" aria-label={`Score: ${analysis?.score ?? 'unavailable'}`}>
                Score <strong>{analysis?.score ?? '—'}</strong>
              </div>
              <div className="detail-row detail-row--block">
                <span className="detail-label">Description</span>
                <strong>{applyingLead.title}</strong>
                {applyingLead.url && (
                  <a href={applyingLead.url} target="_blank" rel="noopener noreferrer">
                    {applyingLead.url}
                  </a>
                )}
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
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary">
                Generate Proposal
              </button>
            </div>
            <div className="view-details">
              <div className="detail-row detail-row--block">
                <span className="detail-label">Proposal</span>
                <span>{analysis?.proposal_draft || 'No proposal draft available.'}</span>
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" disabled>
                Apply
              </button>
            </div>
          </div>
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
