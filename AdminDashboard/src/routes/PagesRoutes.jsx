import { lazy } from 'react';
import Loadable from 'components/Loadable';
import DashboardLayout from 'layout/Dashboard';
import AuthLayout from 'layout/Auth';

const LoginPage = Loadable(lazy(() => import('views/auth/login/Login')));
const RegisterPage = Loadable(lazy(() => import('views/auth/register/Register')));
const ForgotPasswordPage = Loadable(lazy(() => import('views/auth/forgot-password/ForgotPassword')));
const AdminDashboard = Loadable(lazy(() => import('views/navigation/dashboard/AdminDashboard')));
const ClientDashboard = Loadable(lazy(() => import('views/navigation/dashboard/Dashboard')));
const DomainIntegration = Loadable(lazy(() => import('views/navigation/dashboard/Domain')));
const AdminChat = Loadable(lazy(()=>import('views/navigation/dashboard/AdminChatPage')))
const Duration = Loadable(lazy(() => import('views/reporting/Duration')));
const MissedChats = Loadable(lazy(() => import('views/reporting/MissedChats')));
const ChatVolume = Loadable(lazy(() => import('views/reporting/ChatVolume')));
const FirstResponseTime = Loadable(lazy(() => import('views/reporting/FirstResponseTime')));
const UserSatisfaction = Loadable(lazy(() => import('views/reporting/UserSatisfaction')));

const PagesRoutes = {
  path: '/',
  children: [
    {
      path: '/',
      element: <AuthLayout />,
      children: [
        { path: 'login', element: <LoginPage /> },
        { path: 'register', element: <RegisterPage /> },
        { path: 'forgot-password', element: <ForgotPasswordPage /> }
      ]
    },
    {
      path: '/',
      element: <DashboardLayout />,
      children: [
        // { path: 'dashboard-admin', element: <AdminDashboard /> },
        { path: 'dashboard', element: <ClientDashboard /> }, // ✅ fixed route
        { path: 'domain', element: <DomainIntegration /> },
        { path: 'client-chat/:sessionId', element: <AdminChat /> },
        { path: 'duration', element: <Duration /> },
        { path: 'missed-chats', element: <MissedChats /> },
        { path: 'chat-volume', element: <ChatVolume /> },
        { path: 'first-response-time', element: <FirstResponseTime /> },
        { path: 'user-satisfaction', element: <UserSatisfaction /> }
      ]
    }
  ]
};

export default PagesRoutes;
