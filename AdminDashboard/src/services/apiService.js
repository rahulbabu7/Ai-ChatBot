import axios from 'axios';
import { API_URL } from '../config';
// Create axios instance with base configuration
const apiService = axios.create({
  baseURL: API_URL, // Replace with your actual backend URL
  timeout: 10000
});

// Request interceptor to add auth token
apiService.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
    // console.log('Token:', token ? 'Present' : 'Missing');
    // console.log('Request URL:', config.url);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
apiService.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiService;
