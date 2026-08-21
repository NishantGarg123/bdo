import { useEffect, useRef, useState } from 'react';
import { projectsAPI, agentAPI } from '../../services/api';

export default function Agent() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const chatEndRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await projectsAPI.getAll();
        setProjects(res.data);
      } finally {
        setProjectsLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleProjectChange = (e) => {
    setSelectedProject(e.target.value);
    setMessages([]);
  };

  const selectedProjectName = projects.find((p) => String(p.id) === String(selectedProject))?.name || '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || !selectedProject || loading) return;

    const userMsg = { role: 'user', text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, text: m.text }));
      const res = await agentAPI.askQuestion({
        project_id: Number(selectedProject),
        question,
        history,
      });
      const botMsg = {
        role: 'model',
        text: res.data.answer,
        sources: res.data.sources || [],
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errText = err.response?.data?.detail || 'Something went wrong. Please try again.';
      setMessages((prev) => [...prev, { role: 'model', text: errText, error: true }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const suggestedQuestions = [
    'What are the key contacts for this project?',
    'How do I handle emergency situations?',
    'What are the important reference numbers?',
    'What are the common troubleshooting steps?',
  ];

  const handleSuggestion = (q) => {
    setInput(q);
  };

  return (
    <div className="page agent-page">
      <div className="agent-header">
        <div className="agent-header-left">
          <div className="agent-icon-wrap">
            <span className="agent-icon">✦</span>
          </div>
          <div>
            <h1>AI Agent</h1>
            <p>Ask questions about your project's FAQs — powered by AI</p>
          </div>
        </div>
        <div className="agent-header-right">
          {projectsLoading ? (
            <span className="agent-project-loading">Loading projects…</span>
          ) : (
            <div className="agent-project-select-wrap">
              <label htmlFor="agent-project-select">Project</label>
              <select
                id="agent-project-select"
                value={selectedProject}
                onChange={handleProjectChange}
                className="agent-project-select"
              >
                <option value="">— Select a project —</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="agent-chat-container">
        {!selectedProject ? (
          <div className="agent-empty-state">
            <div className="agent-empty-icon">✦</div>
            <h2>Select a project to get started</h2>
            <p>Choose a project from the dropdown above, then ask any question about its FAQs.</p>
          </div>
        ) : messages.length === 0 && !loading ? (
          <div className="agent-empty-state">
            <div className="agent-empty-icon">💬</div>
            <h2>Ask anything about <span className="agent-project-name">{selectedProjectName}</span></h2>
            <p>Your question will be matched against the project's FAQ knowledge base.</p>
            <div className="agent-suggestions">
              {suggestedQuestions.map((q, i) => (
                <button key={i} className="agent-suggestion-chip" onClick={() => handleSuggestion(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="agent-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`agent-message agent-message--${msg.role} ${msg.error ? 'agent-message--error' : ''}`}>
                <div className="agent-message-avatar">
                  {msg.role === 'user' ? '👤' : '✦'}
                </div>
                <div className="agent-message-content">
                  <div className="agent-message-label">{msg.role === 'user' ? 'You' : 'AI Agent'}</div>
                  <div className="agent-message-text">{msg.text}</div>
                  {msg.sources && msg.sources.length > 0 && (
                    <SourceCitations sources={msg.sources} />
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="agent-message agent-message--model">
                <div className="agent-message-avatar">✦</div>
                <div className="agent-message-content">
                  <div className="agent-message-label">AI Agent</div>
                  <div className="agent-typing">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {selectedProject && (
        <form className="agent-input-bar" onSubmit={handleSubmit}>
          <input
            type="text"
            className="agent-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask about ${selectedProjectName}…`}
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            className="btn btn-primary agent-send-btn"
            disabled={!input.trim() || loading}
          >
            {loading ? '…' : 'Ask'}
          </button>
          {messages.length > 0 && (
            <button type="button" className="btn btn-secondary agent-clear-btn" onClick={clearChat} disabled={loading}>
              Clear
            </button>
          )}
        </form>
      )}
    </div>
  );
}

function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="agent-sources">
      <button className="agent-sources-toggle" onClick={() => setOpen(!open)}>
        <span className={`agent-sources-chevron ${open ? 'agent-sources-chevron--open' : ''}`}>▶</span>
        {sources.length} source{sources.length !== 1 ? 's' : ''} referenced
      </button>
      {open && (
        <div className="agent-sources-list">
          {sources.map((s, i) => (
            <div key={i} className="agent-source-item">
              <span className="agent-source-badge">{Math.round(s.score * 100)}%</span>
              <span className="agent-source-question">{s.question}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
