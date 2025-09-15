import { lazy } from 'react';

// project imports
import Loadable from 'components/Loadable';
import DashboardLayout from 'layout/Dashboard';
import AuthLayout from 'layout/Auth';

// Auth pages
const LoginPage = Loadable(lazy(() => import('views/auth/login/Login')));
const RegisterPage = Loadable(lazy(() => import('views/auth/register/Register')));
const ForgotPasswordPage = Loadable(lazy(() => import('views/auth/forgot-password/ForgotPassword')));

// Dashboard pages
const DefaultDashboard = Loadable(lazy(() => import('views/navigation/dashboard/Default')));
const AdminDashboard = Loadable(lazy(() => import('views/navigation/dashboard/AdminDashboard')));
const ClientDashboard = Loadable(lazy(() => import('views/navigation/dashboard/Dashboard'))); // Dashboard.jsx

// ==============================|| APP ROUTING ||============================== //

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
        { path: '/', element: <DefaultDashboard /> },
        { path: 'dashboard-admin', element: <AdminDashboard /> },
        { path: 'dashboard-client', element: <ClientDashboard /> },
        { path: 'client/:clientId', element: <ClientDashboard /> } // ✅ dynamic route for clients
      ]
    }
  ]
};

export default PagesRoutes;
