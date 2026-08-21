import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Leads from './pages/Leads/Leads';
import Activity from './pages/Activity/Activity';
import Integrations from './pages/Integrations/Integrations';
import Projects, { ProjectDetail, IssueDetail, KnowledgeBase } from './pages/Projects/Projects';
import Agent from './pages/Agent/Agent';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/leads" element={<Leads />} />
              <Route
                path="/applied-leads"
                element={
                  <Leads
                    fixedStatus="applied"
                    pageTitle="Applied Leads"
                    pageDescription="View your applied business development leads"
                  />
                }
              />
              <Route
                path="/rejected-leads"
                element={
                  <Leads
                    fixedStatus="rejected"
                    pageTitle="Rejected Leads"
                    pageDescription="View your rejected business development leads"
                  />
                }
              />
              <Route path="/activity" element={<Activity />} />
              <Route path="/integrations" element={<Integrations />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:projectId" element={<ProjectDetail />} />
              <Route path="/projects/:projectId/issues/:issueId" element={<IssueDetail />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
              <Route path="/agent" element={<Agent />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
