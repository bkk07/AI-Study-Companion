import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import Layout from './components/Layout';
import { LoginPage, RegisterPage } from './pages/auth/AuthPages';
import SpacesPage from './pages/SpacesPage';
import ProjectsPage from './pages/ProjectsPage';
import OverviewPage from './pages/project/OverviewPage';
import DocumentsPage from './pages/project/DocumentsPage';
import StructurePage from './pages/project/StructurePage';
import TutorPage from './pages/project/TutorPage';
import FlashcardsPage from './pages/project/FlashcardsPage';
import QuizPage from './pages/project/QuizPage';
import AssessmentsPage from './pages/project/AssessmentsPage';
import DashboardPage from './pages/project/DashboardPage';
import AnalyticsPage from './pages/project/AnalyticsPage';
import ActivityPage from './pages/project/ActivityPage';
import SettingsPage from './pages/project/SettingsPage';
import AdminPage from './pages/AdminPage';

function ActivePage() {
  const { state } = useApp();
  switch (state.view) {
    case 'spaces': return <SpacesPage />;
    case 'projects': return <ProjectsPage />;
    case 'overview': return <OverviewPage />;
    case 'documents': return <DocumentsPage />;
    case 'structure': return <StructurePage />;
    case 'tutor': return <TutorPage />;
    case 'flashcards': return <FlashcardsPage />;
    case 'quiz': return <QuizPage />;
    case 'assessments': return <AssessmentsPage />;
    case 'dashboard': return <DashboardPage />;
    case 'analytics': return <AnalyticsPage />;
    case 'activity': return <ActivityPage />;
    case 'settings': return <SettingsPage />;
    case 'admin': return <AdminPage />;
    default: return <SpacesPage />;
  }
}

function AppShell() {
  const { state } = useApp();
  const { view } = state;

  if (view === 'login') return <LoginPage />;
  if (view === 'register') return <RegisterPage />;

  return (
    <Layout>
      <ActivePage />
    </Layout>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
