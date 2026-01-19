import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const useAuth = (redirectTo = '/login') => {
  const navigate = useNavigate();
  
  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
  
  useEffect(() => {
    if (!token) {
      navigate(redirectTo);
    }
  }, [token, navigate, redirectTo]);
  
  return {
    token,
    isAuthenticated: !!token
  };
};