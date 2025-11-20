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

  // Sample data for AI chatbot response times
  const sampleStatsData = [
    {
      title: 'Average First Response Time',
      value: '0.9s',
      change: '+0.0s',
      changeType: 'positive',
      icon: 'fa-clock',
      color: 'primary'
    },
    {
      title: 'Response Rate',
      value: '99.7%',
      change: '+0.0%',
      changeType: 'positive',
      icon: 'fa-check-circle',
      color: 'success'
    },
    {
      title: 'Instant Responses (<1s)',
      value: '94%',
      change: '+2%',
      changeType: 'positive',
      icon: 'fa-bolt',
      color: 'info'
    },
    {
      title: 'Slow Responses (>3s)',
      value: '0.4%',
      change: '+0.0%',
      changeType: 'positive',
      icon: 'fa-tachometer-alt',
      color: 'warning'
    }
  ];

  // Function to generate dates between start and end date
  const generateDateRange = (start, end) => {
    const dates = [];
    const currentDate = new Date(start);
    const endDate = new Date(end);
    
    while (currentDate <= endDate) {
      dates.push(new Date(currentDate));
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return dates;
  };

  // Function to generate response times for the date range
  const generateResponseTimes = (dates) => {
    return dates.map(date => {
      // Generate realistic response times between 0.5s and 1.2s
      const baseTime = 0.8 + (Math.random() * 0.3);
      return {
        date: date.toISOString().split('T')[0],
        time: Math.max(0.5, Math.min(1.5, baseTime)).toFixed(1),
        day: date.toLocaleDateString('en-US', { weekday: 'short' })
      };
    });
  };

  // Fetch stats data
  const fetchStatsData = async () => {
    try {
      // Using sample data for demo
      setTimeout(() => {
        setStatsData(sampleStatsData);
        setLastUpdated(new Date());
      }, 800); // Simulate API delay
      
    } catch (err) {
      setError(err.message);
      console.error('Error fetching stats:', err);
    }
  };

  // Fetch all data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await fetchStatsData();
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

  // Generate chart data based on selected date range
  const getChartData = () => {
    if (!startDate || !endDate) return [];
    
    const dates = generateDateRange(startDate, endDate);
    return generateResponseTimes(dates);
  };

  const chartData = getChartData();

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
        {statsData.map((stat, index) => (
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
        ))}
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
                  <div className="btn-group mr-4"> {/* Increased margin-right */}
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
                  <div className="mx-3" style={{ width: '20px' }}></div> {/* Added spacer */}
                  
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
              
              {/* Chart with Dynamic Dates */}
              <div className="chart-placeholder" style={{ 
                height: '350px', 
                background: 'linear-gradient(180deg, rgba(4, 169, 245, 0.1) 0%, rgba(4, 169, 245, 0.05) 100%)',
                border: '1px solid #e4e7ea',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#76838f',
                position: 'relative',
                overflow: 'hidden'
              }}>
                {chartData.length > 0 ? (
                  <>
                    {/* Dynamic chart bars based on date range */}
                    <div style={{
                      position: 'absolute',
                      bottom: '50px',
                      left: '40px',
                      right: '40px',
                      height: '200px',
                      display: 'flex',
                      alignItems: 'end',
                      justifyContent: 'space-around'
                    }}>
                      {chartData.map((data, index) => {
                        const time = parseFloat(data.time);
                        // Convert seconds to percentage for visualization (0.5s = 100%, 2s = 0%)
                        const height = Math.max(15, 100 - (time * 80));
                        return (
                          <div key={index} style={{
                            width: `${Math.max(20, 80 / chartData.length)}px`,
                            height: `${height}%`,
                            backgroundColor: time < 0.8 ? '#1bcfb4' : time < 1.2 ? '#04a9f5' : '#fed713',
                            borderRadius: '3px 3px 0 0',
                            position: 'relative',
                            margin: '0 2px'
                          }}>
                            <span style={{
                              position: 'absolute',
                              top: '-35px',
                              left: '50%',
                              transform: 'translateX(-50%)',
                              fontSize: '11px',
                              color: '#76838f',
                              whiteSpace: 'nowrap'
                            }}>
                              {data.date.split('-')[2]}/{data.date.split('-')[1]}
                            </span>
                            <span style={{
                              position: 'absolute',
                              top: '-20px',
                              left: '50%',
                              transform: 'translateX(-50%)',
                              fontSize: '10px',
                              color: '#76838f'
                            }}>
                              {data.day}
                            </span>
                            <span style={{
                              position: 'absolute',
                              bottom: '-25px',
                              left: '50%',
                              transform: 'translateX(-50%)',
                              fontSize: '11px',
                              color: '#76838f',
                              fontWeight: 'bold'
                            }}>
                              {data.time}s
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    
                    <div className="text-center" style={{ zIndex: 1, background: 'rgba(255,255,255,0.9)', padding: '15px', borderRadius: '8px' }}>
                      <i className="fas fa-robot" style={{ fontSize: '36px', marginBottom: '8px', color: '#04a9f5' }}></i>
                      <p className="mb-1">AI Response Times</p>
                      <small className="text-muted">
                        {startDate} to {endDate} • {chartData.length} days
                      </small>
                    </div>
                  </>
                ) : (
                  <div className="text-center">
                    <i className="feather icon-bar-chart-2" style={{ fontSize: '48px', marginBottom: '10px' }}></i>
                    <p>Select a date range to view data</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Response Time Distribution */}
      <div className="row">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Response Time Distribution</h5>
              <div className="mb-4">
                <div className="d-flex justify-content-between mb-1">
                  <span>Instant (&lt; 0.5s)</span>
                  <span className="text-success">45%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-success" style={{ width: '45%' }}></div>
                </div>
              </div>
              <div className="mb-4">
                <div className="d-flex justify-content-between mb-1">
                  <span>Fast (0.5s - 1s)</span>
                  <span className="text-primary">49%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-primary" style={{ width: '49%' }}></div>
                </div>
              </div>
              <div className="mb-4">
                <div className="d-flex justify-content-between mb-1">
                  <span>Acceptable (1s - 2s)</span>
                  <span className="text-warning">5%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-warning" style={{ width: '5%' }}></div>
                </div>
              </div>
              <div>
                <div className="d-flex justify-content-between mb-1">
                  <span>Slow (&gt; 2s)</span>
                  <span className="text-danger">1%</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar bg-danger" style={{ width: '1%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Performance Targets</h5>
              <div className="row text-center">
                <div className="col-4">
                  <div className="border-end">
                    <h4 className="text-success mb-1">94%</h4>
                    <small className="text-muted">&lt; 1s Target</small>
                  </div>
                </div>
                <div className="col-4">
                  <div className="border-end">
                    <h4 className="text-primary mb-1">99.8%</h4>
                    <small className="text-muted">Uptime</small>
                  </div>
                </div>
                <div className="col-4">
                  <h4 className="text-info mb-1">0.8s</h4>
                  <small className="text-muted">Avg Response</small>
                </div>
              </div>
              
              <div className="mt-4 p-3 bg-light rounded">
                <h6 className="text-muted">Performance Status</h6>
                <div className="d-flex align-items-center">
                  <div className="bg-success rounded-circle mr-2" style={{ width: '10px', height: '10px' }}></div>
                  <span className="text-success">Excellent</span>
                  <small className="text-muted ml-2">All targets met</small>
                </div>
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
