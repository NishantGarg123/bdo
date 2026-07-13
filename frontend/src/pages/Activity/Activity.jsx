import { useEffect, useState } from 'react';
import { activityAPI } from '../../services/api';

const ACTIVITY_ICONS = {
  lead_created: '＋',
  lead_updated: '✎',
  applied: '→',
  notes_added: '☰',
  status_changed: '↻',
};

function formatDateTime(dateString) {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Activity() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadActivities = async () => {
      try {
        const response = await activityAPI.getAll();
        setActivities(response.data);
      } catch (err) {
        console.error('Failed to load activities:', err);
      } finally {
        setLoading(false);
      }
    };

    loadActivities();
  }, []);

  if (loading) {
    return <div className="page-loading">Loading activity...</div>;
  }

  return (
    <div className="page activity-page">
      <div className="page-header">
        <h1>Activity</h1>
        <p>Timeline of recent actions and updates</p>
      </div>

      {/* Future: filters by type, user, date range */}
      <div className="timeline-card">
        {activities.length === 0 ? (
          <div className="empty-state">
            <p>No activity yet.</p>
          </div>
        ) : (
          <ul className="timeline">
            {activities.map((activity) => (
              <li key={activity.id} className="timeline-item">
                <div className="timeline-icon">
                  {ACTIVITY_ICONS[activity.activity_type] || '•'}
                </div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="timeline-type">{activity.activity_type_display}</span>
                    <span className="timeline-date">{formatDateTime(activity.created_at)}</span>
                  </div>
                  <p className="timeline-description">
                    {activity.description}
                    {activity.lead_title && (
                      <span className="timeline-lead"> — {activity.lead_title}</span>
                    )}
                  </p>
                  <span className="timeline-user">by {activity.username}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
