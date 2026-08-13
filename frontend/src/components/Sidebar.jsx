import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '○' },
  { path: '/leads', label: 'Leads', icon: '◉' },
  { path: '/projects', label: 'Projects', icon: '◆' },
  { path: '/knowledge-base', label: 'Knowledge Base', icon: '▤' },
  { path: '/activity', label: 'Activity', icon: '◷' },
  { path: '/integrations', label: 'Integrations', icon: '⬡' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand"><span className="brand-icon">B</span><div><h1>BDO Leads</h1><p>Lead Management</p></div></div>
      <nav className="sidebar-nav">
        {navItems.map((item) => <NavLink key={item.path} to={item.path} className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`}><span className="sidebar-link-icon">{item.icon}</span>{item.label}</NavLink>)}
      </nav>
    </aside>
  );
}
