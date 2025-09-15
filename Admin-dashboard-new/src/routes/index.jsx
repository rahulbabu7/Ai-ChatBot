import { createBrowserRouter, Navigate } from 'react-router-dom';

// project-imports
import PagesRoutes from './PagesRoutes';
import NavigationRoutes from './NavigationRoutes';
import ComponentsRoutes from './ComponentsRoutes';
import FormsRoutes from './FormsRoutes';
import TablesRoutes from './TablesRoutes';
import ChartMapRoutes from './ChartMapRoutes';
import OtherRoutes from './OtherRoutes';

// custom imports
import Login from '../views/auth/login/Login';
import DefaultPage from '../views/navigation/dashboard/Default';

const router = createBrowserRouter(
  [
    // redirect base path to login
    {
      path: '/demos/admin-templates/datta-able/react/free/login/',
      element: (
        <Navigate
          to="/demos/admin-templates/datta-able/react/free/login/"
          replace
        />
      )
    },

    // login route
    {
      path: '/demos/admin-templates/datta-able/react/free/login/',
      element: <Login />
    },

    // dashboard route
    {
      path: '/demos/admin-templates/datta-able/react/free/dashboard/:clientId',
      element: <DefaultPage />
    },

    // existing template routes
    NavigationRoutes,
    ComponentsRoutes,
    FormsRoutes,
    TablesRoutes,
    ChartMapRoutes,
    PagesRoutes,
    OtherRoutes
  ],
  {
    basename: import.meta.env.VITE_APP_BASE_NAME
  }
);

export default router;
