// src/components/PrivateRoute.tsx
import { Navigate } from "react-router-dom";
import { ReactNode } from "react";

interface PrivateRouteProps {
  children: ReactNode;
  role?: string; // "admin" or "client"
}

const PrivateRoute = ({ children, role }: PrivateRouteProps) => {
  const token = localStorage.getItem("token");
  const userRole = localStorage.getItem("role");

  if (!token) {
    return <Navigate to="/login" />;
  }

  if (role && userRole !== role) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>; // 👈 wrap in fragment to render children
};

export default PrivateRoute;