import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_URL } from '../../config';

const FirstResponseTime = () => {
  const [timeRange, setTimeRange] = useState('week');
  const [dailyStats, setDailyStats] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({
    total_sessions: 0,
    today_sessions: 0,
    today_visitors: 0,
    active_users_now: 0,
    avg_response_time: 0.0,
    total_messages: 0
  });
  const [responseTimeStats, setResponseTimeStats] = useState({
    avg_response_time: 0.0,
    min_response_time: 0.0,
    max_response_time: 0.0,
    median_response_time: 0.0,
    instant_responses: 0,
    fast_responses: 0,
    slow_responses: 0,
    total_responses: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Get auth token
  const getAuthToken = () => {
    return localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
  };

  // Create axios instance
  const createApi = () => {
    return axios.create({
      baseURL: API_URL,
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`,
        'Content-Type': 'application/json'
      }
    });
  };

  // Initialize dates
  useEffect(() => {
    const today = new Date();
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(today.getDate() - 7);
    
    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(oneWeekAgo.toISOString().split('T')[0]);
  }, []);

  // Fetch daily stats
  const fetchDailyStats = useCallback(async (start, end) => {
    try {
      const api = createApi();
      const response = await api.get('/client/stats/daily', {
        params: { start_date: start, end_date: end }
      });
      setDailyStats(response.data.daily_stats || []);
    } catch (err) {
      console.error('❌ Error fetching daily stats:', err);
      throw err;
    }
  }, []);

  // Fetch dashboard stats
  const fetchDashboardStats = useCallback(async () => {
    try {
      const api = createApi();
      const response = await api.get('/client/stats/dashboard');
      setDashboardStats(response.data);
    } catch (err) {
      console.error('❌ Error fetching dashboard stats:', err);
      throw err;
    }
  }, []);

  // Fetch response time stats
  const fetchResponseTimeStats = useCallback(async () => {
    try {
      const api = createApi();
      const response = await api.get('/client/stats/response-time', {
        params: { days: 7 }
      });
      setResponseTimeStats(response.data);
    } catch (err) {
      console.error('❌ Error fetching response time stats:', err);
      throw err;
    }
  }, []);

  // Fetch all data
  const fetchAllData = useCallback(async () => {
    if (!startDate || !endDate) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchDailyStats(startDate, endDate),
        fetchDashboardStats(),
        fetchResponseTimeStats()
      ]);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, fetchDailyStats, fetchDashboardStats, fetchResponseTimeStats]);

  // Load data when dates change
  useEffect(() => {
    if (startDate && endDate) {
      fetchAllData();
    }
  }, [startDate, endDate, fetchAllData]);

  // Format response time
  const formatResponseTime = (seconds) => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`;
    }
    return `${seconds.toFixed(1)}s`;
  };

  // Calculate average response time from daily stats
  const calculateAverageResponseTime = () => {
    if (!dailyStats || dailyStats.length === 0) return '0.0s';
    
    const statsWithResponseTime = dailyStats.filter(day => day.avg_response_time > 0);
    if (statsWithResponseTime.length === 0) return '0.0s';
    
    const totalResponseTime = statsWithResponseTime.reduce(
      (sum, day) => sum + day.avg_response_time, 
      0
    );
    const avgTime = totalResponseTime / statsWithResponseTime.length;
    return formatResponseTime(avgTime);
  };

  // Calculate response rate
  const calculateResponseRate = () => {
    const totalChats = dailyStats.reduce((sum, day) => sum + (day.chats || 0), 0);
    const totalVisitors = dailyStats.reduce((sum, day) => sum + (day.visitors || 0), 0);
    
    if (totalVisitors === 0) return '0%';
    const rate = (totalChats / totalVisitors) * 100;
    return `${Math.min(100, rate).toFixed(1)}%`;
  };

  // Calculate total messages
  const calculateTotalMessages = () => {
    return dailyStats.reduce((sum, day) => sum + (day.chats || 0), 0);
  };

  // Calculate engagement metrics
  const calculateEngagementMetrics = () => {
    const totalChats = calculateTotalMessages();
    const totalVisitors = dailyStats.reduce((sum, day) => sum + (day.visitors || 0), 0);
    
    if (totalVisitors === 0) return {
      avgMessagesPerUser: '0.0',
      engagement: '0%'
    };
    
    const avgMessages = (totalChats / totalVisitors).toFixed(1);
    const engagementRate = Math.min(100, (totalVisitors / dailyStats.length) * 10).toFixed(0);
    
    return {
      avgMessagesPerUser: avgMessages,
      engagement: `${engagementRate}%`
    };
  };

  // Calculate response time distribution percentages
  const calculateResponseTimeDistribution = () => {
    const total = responseTimeStats.total_responses;
    if (total === 0) return { instant: 0, fast: 0, acceptable: 0, slow: 0 };
    
    return {
      instant: ((responseTimeStats.instant_responses / total) * 100).toFixed(0),
      fast: ((responseTimeStats.fast_responses / total) * 100).toFixed(0),
      slow: ((responseTimeStats.slow_responses / total) * 100).toFixed(0)
    };
  };

  // Stats cards data
  const getStatsCards = () => {
    const metrics = calculateEngagementMetrics();
    
    return [
      {
        title: 'Total Sessions',
        value: dashboardStats.total_sessions.toLocaleString(),
        change: `+${dashboardStats.today_sessions} today`,
        changeType: 'positive',
        icon: 'fa-users',
        color: 'primary'
      },
      {
        title: 'Avg Response Time',
        value: formatResponseTime(dashboardStats.avg_response_time),
        change: `${responseTimeStats.total_responses} responses`,
        changeType: 'positive',
        icon: 'fa-bolt',
        color: 'success'
      },
      {
        title: 'Today\'s Visitors',
        value: dashboardStats.today_visitors.toString(),
        change: `${dashboardStats.active_users_now} active now`,
        changeType: 'positive',
        icon: 'fa-chart-line',
        color: 'info'
      },
      {
        title: 'Total Messages',
        value: dashboardStats.total_messages.toLocaleString(),
        change: metrics.avgMessagesPerUser + ' avg/user',
        changeType: 'positive',
        icon: 'fa-comments',
        color: 'warning'
      }
    ];
  };

  // Refresh data
  const handleRefresh = () => {
    fetchAllData();
  };

  // Quick date range presets
  const setQuickDateRange = (range) => {
    const today = new Date();
    const newStartDate = new Date();
    
    switch (range) {
      case 'today':
        newStartDate.setDate(today.getDate());
        break;
      case 'week':
        newStartDate.setDate(today.getDate() - 6);
        break;
      case 'month':
        newStartDate.setDate(today.getDate() - 29);
        break;
      default:
        newStartDate.setDate(today.getDate() - 6);
    }
    
    setStartDate(newStartDate.toISOString().split('T')[0]);
    setEndDate(today.toISOString().split('T')[0]);
    setTimeRange(range);
  };

  // Format last updated time
  const formatLastUpdated = () => {
    if (!lastUpdated) return '';
    return lastUpdated.toLocaleTimeString();
  };

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDashboardStats();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardStats]);

  // Get days in range
  const getDaysInRange = () => {
    if (!startDate || !endDate) return 0;
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  };

  // Loading state
  if (loading && dailyStats.length === 0) {
    return (
      <div className="page-content">
        <div className="container-fluid">
          <div className="row">
            <div className="col-12 text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="mt-2">Loading analytics data...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="page-content">
        <div className="container-fluid">
          <div className="row">
            <div className="col-12">
              <div className="alert alert-danger" role="alert">
                <h4 className="alert-heading">Error Loading Data</h4>
                <p>{error}</p>
                <button className="btn btn-primary" onClick={handleRefresh}>Try Again</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statsCards = getStatsCards();
  const metrics = calculateEngagementMetrics();
  const daysInRange = getDaysInRange();
  const distribution = calculateResponseTimeDistribution();

  return (
    <div className="page-content">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-block">
          <div className="row align-items-center">
            <div className="col-md-8">
              <div className="page-header-title">
                <h4 className="m-b-5">Analytics Dashboard</h4>
              </div>
              <ul className="breadcrumb">
                <li className="breadcrumb-item"><a href="/">Reporting</a></li>
                <li className="breadcrumb-item active">Analytics</li>
              </ul>
            </div>
            <div className="col-md-4 text-right">
              <div className="d-flex align-items-center justify-content-end">
                <small className="text-muted mr-3">Last updated: {formatLastUpdated()}</small>
                <button className="btn btn-primary btn-sm" onClick={handleRefresh} disabled={loading}>
                  <i className={`feather icon-refresh-cw mr-2 ${loading ? 'spin' : ''}`}></i>
                  Refresh
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="row">
        {statsCards.map((stat, index) => (
          <div className="col-xl-3 col-md-6" key={index}>
            <div className="card card-statistics">
              <div className="card-body">
                <div className="d-flex align-items-center">
                  <div className={`bg-${stat.color} rounded-circle p-3 mr-3`}>
                    <i className={`fas ${stat.icon} text-white`} style={{ fontSize: '24px' }}></i>
                  </div>
                  <div className="flex-grow-1">
                    <h4 className="mb-0">{stat.value}</h4>
                    <p className="text-muted mb-1">{stat.title}</p>
                    {stat.change && (
                      <small className="text-success">
                        <i className="fas fa-arrow-up mr-1"></i>
                        {stat.change}
                      </small>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Chart Section */}
      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h5 className="card-title mb-0">
                  Daily Activity Trend 
                  <small className="text-muted ml-2">({daysInRange} {daysInRange === 1 ? 'day' : 'days'})</small>
                </h5>
                <div className="btn-group">
                  <button
                    className={`btn btn-sm ${timeRange === 'today' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setQuickDateRange('today')}
                  >
                    Today
                  </button>
                  <button
                    className={`btn btn-sm ${timeRange === 'week' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setQuickDateRange('week')}
                  >
                    7 Days
                  </button>
                  <button
                    className={`btn btn-sm ${timeRange === 'month' ? 'btn-primary' : 'btn-outline-primary'}`}
                    onClick={() => setQuickDateRange('month')}
                  >
                    30 Days
                  </button>
                </div>
              </div>
              
              {/* Chart - Same as before */}
              <div className="chart-container" style={{
                height: '350px',
                background: 'linear-gradient(180deg, rgba(4, 169, 245, 0.05) 0%, rgba(4, 169, 245, 0.02) 100%)',
                border: '1px solid var(--bs-border-color)',
                borderRadius: '8px',
                padding: '20px',
                position: 'relative'
              }}>
                {dailyStats.length > 0 ? (
                  <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', height: '100%', paddingTop: '40px' }}>
                    {dailyStats.map((day, index) => {
                      const maxValue = Math.max(...dailyStats.map(d => Math.max(d.visitors, d.chats)), 1);
                      const visitorHeight = (day.visitors / maxValue) * 100;
                      const chatHeight = (day.chats / maxValue) * 100;
                      
                      return (
                        <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, maxWidth: daysInRange > 7 ? '60px' : '100px' }}>
                          <div className="text-muted" style={{ fontSize: '11px', marginBottom: '10px', fontWeight: '500' }}>
                            {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '200px', marginBottom: '10px' }}>
                            <div style={{ width: daysInRange > 7 ? '15px' : '20px', height: `${Math.max(5, visitorHeight)}%`, backgroundColor: '#04a9f5', borderRadius: '3px 3px 0 0', position: 'relative', transition: 'height 0.3s ease' }}>
                              {day.visitors > 0 && <span style={{ position: 'absolute', top: '-20px', left: '50%', transform: 'translateX(-50%)', fontSize: '10px', color: '#04a9f5', fontWeight: 'bold' }}>{day.visitors}</span>}
                            </div>
                            <div style={{ width: daysInRange > 7 ? '15px' : '20px', height: `${Math.max(5, chatHeight)}%`, backgroundColor: '#1bcfb4', borderRadius: '3px 3px 0 0', position: 'relative', transition: 'height 0.3s ease' }}>
                              {day.chats > 0 && <span style={{ position: 'absolute', top: '-20px', left: '50%', transform: 'translateX(-50%)', fontSize: '10px', color: '#1bcfb4', fontWeight: 'bold' }}>{day.chats}</span>}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center" style={{ paddingTop: '100px' }}>
                    <i className="feather icon-bar-chart-2" style={{ fontSize: '48px', color: '#ccc' }}></i>
                    <p className="text-muted mt-3">No data available</p>
                  </div>
                )}
                <div style={{ position: 'absolute', bottom: '20px', left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: '30px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '12px', height: '12px', backgroundColor: '#04a9f5', borderRadius: '2px' }}></div>
                    <span>Visitors</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '12px', height: '12px', backgroundColor: '#1bcfb4', borderRadius: '2px' }}></div>
                    <span>Messages</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Response Time Distribution & Performance */}
      <div className="row">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Response Time Distribution</h5>
              <div className="mb-4">
                <div className="d-flex justify-content-between mb-1">
                  <span>Instant (&lt; 1s)</span>
                  <span className="text-success">{distribution.instant}%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-success" style={{ width: `${distribution.instant}%` }}></div>
                </div>
              </div>
              <div className="mb-4">
                <div className="d-flex justify-content-between mb-1">
                  <span>Fast (1s - 2s)</span>
                  <span className="text-primary">{distribution.fast}%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-primary" style={{ width: `${distribution.fast}%` }}></div>
                </div>
              </div>
              <div>
                <div className="d-flex justify-content-between mb-1">
                  <span>Slow (&gt; 2s)</span>
                  <span className="text-danger">{distribution.slow}%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-danger" style={{ width: `${distribution.slow}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Performance Summary</h5>
              <div className="row text-center">
                <div className="col-4">
                  <div className="border-end">
                    <h4 className="text-success mb-1">{formatResponseTime(responseTimeStats.avg_response_time)}</h4>
                    <small className="text-muted">Average</small>
                  </div>
                </div>
                <div className="col-4">
                  <div className="border-end">
                    <h4 className="text-primary mb-1">{formatResponseTime(responseTimeStats.median_response_time)}</h4>
                    <small className="text-muted">Median</small>
                  </div>
                </div>
                <div className="col-4">
                  <h4 className="text-info mb-1">{formatResponseTime(responseTimeStats.max_response_time)}</h4>
                  <small className="text-muted">Max</small>
                </div>
              </div>
              
              <div className="mt-4 p-3 bg-light rounded">
                <h6 className="text-muted mb-2">System Status</h6>
                <div className="d-flex align-items-center justify-content-between">
                  <div className="d-flex align-items-center">
                    <div className="bg-success rounded-circle mr-2" style={{ width: '10px', height: '10px' }}></div>
                    <span className="text-success font-weight-bold">Operational</span>
                  </div>
                  <small className="text-muted">{dashboardStats.active_users_now} active users</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .card-statistics { transition: transform 0.2s, box-shadow 0.2s; }
        .card-statistics:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
      `}</style>
    </div>
  );
};

export default FirstResponseTime;