import React, { useState, useEffect } from 'react';

const FirstResponseTime = () => {
  const [timeRange, setTimeRange] = useState('week');
  const [statsData, setStatsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Initialize dates on component mount
  useEffect(() => {
    const today = new Date();
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(today.getDate() - 7);
    
    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(oneWeekAgo.toISOString().split('T')[0]);
    fetchData(); // Load initial data
  }, []);

  // Fetch stats data from backend
  const fetchStatsData = async () => {
    try {
      const response = await fetch('/api/reporting/first-response-time/stats', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch stats data');
      }
      
      const data = await response.json();
      setStatsData(data);
      
    } catch (err) {
      setError(err.message);
      console.error('Error fetching stats:', err);
    }
  };

  // Fetch chart data from backend
  const fetchChartData = async () => {
    try {
      const response = await fetch(`/api/reporting/first-response-time/chart?startDate=${startDate}&endDate=${endDate}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch chart data');
      }
      
      const data = await response.json();
      return data;
      
    } catch (err) {
      setError(err.message);
      console.error('Error fetching chart data:', err);
      return [];
    }
  };

  // Fetch all data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchStatsData(),
        // fetchChartData() - Uncomment when you have chart data endpoint
      ]);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch data when timeRange or dates change
  useEffect(() => {
    if (startDate && endDate) {
      fetchData();
    }
  }, [timeRange, startDate, endDate]);

  // Refresh data function
  const handleRefresh = () => {
    fetchData();
  };

  // Handle date range change
  const handleDateRangeChange = () => {
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      
      if (start > end) {
        setError('Start date cannot be after end date');
        return;
      }
      
      fetchData();
    }
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
        newStartDate.setDate(today.getDate() - 7);
        break;
      case 'month':
        newStartDate.setMonth(today.getMonth() - 1);
        break;
      case 'quarter':
        newStartDate.setMonth(today.getMonth() - 3);
        break;
      default:
        newStartDate.setDate(today.getDate() - 7);
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

  // Loading state
  if (loading) {
    return (
      <div className="page-content">
        <div className="page-header">
          <div className="page-block">
            <div className="row align-items-center">
              <div className="col-md-12">
                <div className="page-header-title">
                  <h4 className="m-b-10">First Response Time</h4>
                </div>
                <ul className="breadcrumb">
                  <li className="breadcrumb-item">
                    <a href="/">
                      <i className="feather icon-home"></i>
                    </a>
                  </li>
                  <li className="breadcrumb-item">
                    <a href="#!">Reporting</a>
                  </li>
                  <li className="breadcrumb-item">
                    <a href="#!">Analytics</a>
                  </li>
                  <li className="breadcrumb-item active">First Response Time</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        
        <div className="container-fluid">
          <div className="row">
            <div className="col-12 text-center">
              <div className="spinner-border text-primary" role="status">
                <span className="sr-only">Loading...</span>
              </div>
              <p className="mt-2">Loading data...</p>
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
        <div className="page-header">
          <div className="page-block">
            <div className="row align-items-center">
              <div className="col-md-12">
                <div className="page-header-title">
                  <h4 className="m-b-10">First Response Time</h4>
                </div>
                <ul className="breadcrumb">
                  <li className="breadcrumb-item">
                    <a href="/">
                      <i className="feather icon-home"></i>
                    </a>
                  </li>
                  <li className="breadcrumb-item">
                    <a href="#!">Reporting</a>
                  </li>
                  <li className="breadcrumb-item">
                    <a href="#!">Analytics</a>
                  </li>
                  <li className="breadcrumb-item active">First Response Time</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        
        <div className="container-fluid">
          <div className="row">
            <div className="col-12">
              <div className="alert alert-danger" role="alert">
                <h4 className="alert-heading">Error Loading Data</h4>
                <p>{error}</p>
                <button className="btn btn-primary" onClick={handleRefresh}>
                  Try Again
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-block">
          <div className="row align-items-center">
            <div className="col-md-8">
              <div className="page-header-title">
                <h4 className="m-b-5">First Response Time</h4>
              </div>
              <ul className="breadcrumb">
                <li className="breadcrumb-item">
                  <a href="/">Reporting</a>
                </li>
                <li className="breadcrumb-item">
                  <a href="#!">Analytics</a>
                </li>
                <li className="breadcrumb-item active">First Response Time</li>
              </ul>
            </div>
            <div className="col-md-4 text-right">
              <div className="d-flex align-items-center justify-content-end">
                <small className="text-muted mr-3">
                  Last updated: {formatLastUpdated()}
                </small>
                <button 
                  className="btn btn-primary btn-sm"
                  onClick={handleRefresh}
                  disabled={loading}
                >
                  <i className={`feather icon-refresh-cw mr-2 ${loading ? 'spin' : ''}`}></i>
                  Refresh Data
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="row">
        {statsData.length > 0 ? (
          statsData.map((stat, index) => (
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
                        <small className={`text-${stat.changeType === 'positive' ? 'success' : 'danger'}`}>
                          <i className={`fas fa-arrow-${stat.changeType === 'positive' ? 'down' : 'up'} mr-1`}></i>
                          {stat.change} from last week
                        </small>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          // Empty state when no data
          [1, 2, 3, 4].map((index) => (
            <div className="col-xl-3 col-md-6" key={index}>
              <div className="card card-statistics">
                <div className="card-body">
                  <div className="d-flex align-items-center">
                    <div className="bg-secondary rounded-circle p-3 mr-3">
                      <i className="fas fa-chart-line text-white" style={{ fontSize: '24px' }}></i>
                    </div>
                    <div className="flex-grow-1">
                      <h4 className="mb-0">--</h4>
                      <p className="text-muted mb-1">No Data Available</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Chart Section */}
      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h5 className="card-title mb-0">AI Response Time Trend</h5>
                <div className="d-flex align-items-center">
                  {/* Quick Date Range Buttons */}
                  <div className="btn-group mr-4">
                    <button
                      className={`btn btn-sm ${timeRange === 'today' ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => setQuickDateRange('today')}
                      disabled={loading}
                    >
                      Today
                    </button>
                    <button
                      className={`btn btn-sm ${timeRange === 'week' ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => setQuickDateRange('week')}
                      disabled={loading}
                    >
                      Week
                    </button>
                    <button
                      className={`btn btn-sm ${timeRange === 'month' ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => setQuickDateRange('month')}
                      disabled={loading}
                    >
                      Month
                    </button>
                    <button
                      className={`btn btn-sm ${timeRange === 'quarter' ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => setQuickDateRange('quarter')}
                      disabled={loading}
                    >
                      Quarter
                    </button>
                  </div>
                  
                  {/* Spacer between Quarter and date picker */}
                  <div className="mx-3" style={{ width: '20px' }}></div>
                  
                  {/* Date Range Picker */}
                  <div className="d-flex align-items-center">
                    <div className="input-group input-group-sm mr-2">
                      <input 
                        type="date" 
                        className="form-control"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        disabled={loading}
                        style={{ width: '130px' }}
                      />
                    </div>
                    
                    <span className="mr-2 text-muted">to</span>
                    
                    <div className="input-group input-group-sm mr-2">
                      <input 
                        type="date" 
                        className="form-control"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        disabled={loading}
                        style={{ width: '130px' }}
                      />
                    </div>
                    
                    <button 
                      className="btn btn-primary btn-sm"
                      onClick={handleDateRangeChange}
                      disabled={loading}
                    >
                      Apply
                    </button>
                  </div>
                </div>
              </div>
              
              {/* Chart Placeholder - Replace with actual chart when backend is ready */}
              <div className="chart-placeholder" style={{ 
                height: '350px', 
                background: 'linear-gradient(180deg, rgba(4, 169, 245, 0.1) 0%, rgba(4, 169, 245, 0.05) 100%)',
                border: '1px solid #e4e7ea',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#76838f',
                position: 'relative'
              }}>
                <div className="text-center">
                  <i className="feather icon-bar-chart-2" style={{ fontSize: '48px', marginBottom: '10px' }}></i>
                  <p>Chart Data</p>
                  <small className="text-muted">
                    Connect to backend API to display response time trends
                  </small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Response Time Distribution - Remove or connect to backend */}
      <div className="row">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Response Time Distribution</h5>
              <div className="text-center py-4">
                <i className="feather icon-pie-chart" style={{ fontSize: '48px', color: '#6c757d' }}></i>
                <p className="mt-2 text-muted">Connect to backend for distribution data</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Performance Targets</h5>
              <div className="text-center py-4">
                <i className="feather icon-target" style={{ fontSize: '48px', color: '#6c757d' }}></i>
                <p className="mt-2 text-muted">Connect to backend for target data</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add CSS for spinning refresh icon */}
      <style>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default FirstResponseTime;
