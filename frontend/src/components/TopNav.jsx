import { useAuth } from '../context/AuthContext';

export default function TopNav() {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <header className="topnav">
      <div className="topnav-left">
        <h2 className="topnav-title">Welcome back</h2>
        <p className="topnav-subtitle">Manage your leads and track progress</p>
      </div>

      <div className="topnav-right">
        <div className="user-badge">
          <span className="user-avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</span>
          <span className="user-name">{user?.username}</span>
        </div>
        <button type="button" className="btn btn-ghost" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}
