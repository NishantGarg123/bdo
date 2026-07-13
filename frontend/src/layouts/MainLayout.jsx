import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TopNav from '../components/TopNav';

export default function MainLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <TopNav />
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
