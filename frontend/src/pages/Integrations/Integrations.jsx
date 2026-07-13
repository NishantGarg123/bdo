import { useEffect, useState } from 'react';
import { integrationsAPI } from '../../services/api';

const INTEGRATION_ICONS = {
  linkedin: 'in',
  gmail: 'G',
  outlook: 'O',
  'job-portals': 'JP',
  'ats-platforms': 'ATS',
};

export default function Integrations() {
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadIntegrations = async () => {
      try {
        const response = await integrationsAPI.getAll();
        setIntegrations(response.data);
      } catch (err) {
        console.error('Failed to load integrations:', err);
      } finally {
        setLoading(false);
      }
    };

    loadIntegrations();
  }, []);

  if (loading) {
    return <div className="page-loading">Loading integrations...</div>;
  }

  return (
    <div className="page integrations-page">
      <div className="page-header">
        <h1>Integrations</h1>
        <p>Connect external services to streamline your workflow</p>
      </div>

      {/* Future: OAuth flows, sync settings, webhooks */}
      <div className="integrations-grid">
        {integrations.map((integration) => (
          <div key={integration.id} className="integration-card">
            <div className="integration-icon">
              {INTEGRATION_ICONS[integration.slug] || integration.name[0]}
            </div>
            <div className="integration-info">
              <h3>{integration.name}</h3>
              <p>{integration.description}</p>
              <span className={`integration-status integration-status--${integration.status}`}>
                {integration.status_display}
              </span>
            </div>
            <button type="button" className="btn btn-secondary" disabled>
              Connect
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
