import { useEffect, useState } from 'react';
import StatCard from '../../components/StatCard';
import { dashboardAPI } from '../../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await dashboardAPI.getStats();
        setStats(response.data);
      } catch (err) {
        console.error('Failed to load dashboard stats:', err);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  if (loading) {
    return <div className="page-loading">Loading dashboard...</div>;
  }

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your lead pipeline</p>
      </div>

      <div className="stats-grid">
        <StatCard title="Total Leads" value={stats?.total_leads ?? 0} variant="primary" />
        <StatCard title="Pending Leads" value={stats?.pending_leads ?? stats?.new_leads ?? 0} variant="info" />
        <StatCard title="Applied Leads" value={stats?.applied_leads ?? 0} variant="success" />
        <StatCard title="Rejected Leads" value={stats?.rejected_leads ?? 0} variant="danger" />
      </div>

      {/* Future: charts, analytics, date range filters */}
      <div className="chart-placeholder">
        <div className="chart-placeholder-content">
          <h3>Analytics</h3>
          <p>Charts and detailed analytics will appear here.</p>
          <span className="placeholder-badge">Coming Soon</span>
        </div>
      </div>
    </div>
  );
}
