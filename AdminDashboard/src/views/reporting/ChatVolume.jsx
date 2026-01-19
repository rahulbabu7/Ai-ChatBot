// src/views/reporting/ChatVolume.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  TextField,
  MenuItem,
  IconButton,
  Tooltip,
  Paper,
  Chip,
  Switch,
  FormControlLabel,
  Alert,
  LinearProgress,
  Snackbar,
  CircularProgress
} from '@mui/material';
import {
  FilterList,
  Refresh,
  TrendingUp,
  ChatBubbleOutline,
  People,
  Schedule,
  PlayArrow,
  Pause,
  Wifi,
  WifiOff
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';

// API service functions
const chatVolumeAPI = {
  // Fetch historical chat volume data
  getHistoricalData: async (filters = {}) => {
    const queryParams = new URLSearchParams();
    
    if (filters.dateRange) {
      queryParams.append('dateRange', filters.dateRange);
    }
    if (filters.viewType) {
      queryParams.append('viewType', filters.viewType);
    }

    const response = await fetch(`/api/chat-volume/historical?${queryParams}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch historical chat volume data');
    }
    
    return await response.json();
  },

  // Get real-time chat volume stats
  getRealTimeStats: async () => {
    const response = await fetch('/api/chat-volume/realtime/stats');
    
    if (!response.ok) {
      throw new Error('Failed to fetch real-time stats');
    }
    
    return await response.json();
  },

  // Get overall statistics
  getOverallStats: async (dateRange = '24hours') => {
    const response = await fetch(`/api/chat-volume/stats?dateRange=${dateRange}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch overall statistics');
    }
    
    return await response.json();
  }
};

// Real WebSocket service for live data
const createWebSocketService = (onDataUpdate, onStatusChange) => {
  let ws = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      // Replace with your actual WebSocket endpoint
      ws = new WebSocket('ws://localhost:3001/api/chat-volume/live');
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
        onStatusChange('connected');
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event);
        onStatusChange('disconnected');
        
        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            reconnectAttempts++;
            connect();
          }, 3000);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onStatusChange('error');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onDataUpdate(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      onStatusChange('error');
    }
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
      ws = null;
    }
    reconnectAttempts = maxReconnectAttempts; // Stop reconnection attempts
  };

  return {
    connect,
    disconnect,
    isConnected: () => ws && ws.readyState === WebSocket.OPEN
  };
};

const ChatVolume = () => {
  useAuth();
  
  const [historicalData, setHistoricalData] = useState([]);
  const [realTimeData, setRealTimeData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [realTimeEnabled, setRealTimeEnabled] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [filters, setFilters] = useState({
    dateRange: '24hours',
    viewType: 'volume'
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [overallStats, setOverallStats] = useState({
    totalChats: 0,
    answeredChats: 0,
    missedChats: 0,
    avgResponseTime: '0.0',
    currentVolume: 0,
    operatorsOnline: 0
  });
  
  const webSocketService = useRef(null);

  // Date range options
  const dateRangeOptions = [
    { value: '1hour', label: 'Last Hour' },
    { value: '4hours', label: 'Last 4 Hours' },
    { value: '8hours', label: 'Last 8 Hours' },
    { value: '24hours', label: 'Last 24 Hours' },
    { value: '7days', label: 'Last 7 Days' },
    { value: '30days', label: 'Last 30 Days' }
  ];

  const viewTypeOptions = [
    { value: 'volume', label: 'Chat Volume' },
    { value: 'response', label: 'Response Time' },
    { value: 'operators', label: 'Operators Online' }
  ];

  // Initialize WebSocket service
  useEffect(() => {
    webSocketService.current = createWebSocketService(
      handleRealTimeData,
      handleConnectionStatus
    );

    return () => {
      if (webSocketService.current) {
        webSocketService.current.disconnect();
      }
    };
  }, []);

  // Load initial data
  useEffect(() => {
    loadHistoricalData();
    loadOverallStats();
  }, [filters.dateRange]);

  // Handle real-time data updates
  const handleRealTimeData = (newData) => {
    setRealTimeData(prev => {
      const updated = [...prev, newData];
      // Keep only last 100 data points for performance
      return updated.slice(-100);
    });
    
    // Update overall stats with real-time data
    setOverallStats(prev => ({
      ...prev,
      currentVolume: newData.incoming || 0,
      operatorsOnline: newData.operatorsOnline || 0
    }));
  };

  const handleConnectionStatus = (status) => {
    setConnectionStatus(status);
    
    if (status === 'error') {
      showSnackbar('Failed to connect to live data feed', 'error');
    } else if (status === 'connected') {
      showSnackbar('Live data connected successfully', 'success');
    }
  };

  // Load historical data from API
  const loadHistoricalData = async () => {
    try {
      setLoading(true);
      const response = await chatVolumeAPI.getHistoricalData(filters);
      
      // Transform API response to match chart data structure
      const transformedData = response.data?.map(item => ({
        timestamp: item.timestamp || item.date,
        date: item.date,
        hour: item.hour,
        incoming: item.incoming || item.totalChats || 0,
        answered: item.answered || item.answeredChats || 0,
        missed: item.missed || item.missedChats || 0,
        responseTime: item.responseTime || item.avgResponseTime || 0,
        operatorsOnline: item.operatorsOnline || item.activeOperators || 0
      })) || [];
      
      setHistoricalData(transformedData);
    } catch (error) {
      console.error('Error loading historical data:', error);
      showSnackbar('Failed to load historical data', 'error');
      setHistoricalData([]);
    } finally {
      setLoading(false);
    }
  };

  // Load overall statistics
  const loadOverallStats = async () => {
    try {
      const response = await chatVolumeAPI.getOverallStats(filters.dateRange);
      setOverallStats({
        totalChats: response.totalChats || 0,
        answeredChats: response.answeredChats || 0,
        missedChats: response.missedChats || 0,
        avgResponseTime: response.avgResponseTime?.toFixed(1) || '0.0',
        currentVolume: response.currentVolume || 0,
        operatorsOnline: response.operatorsOnline || 0
      });
    } catch (error) {
      console.error('Error loading overall stats:', error);
      showSnackbar('Failed to load statistics', 'error');
    }
  };

  // Load real-time stats
  const loadRealTimeStats = async () => {
    try {
      const response = await chatVolumeAPI.getRealTimeStats();
      setOverallStats(prev => ({
        ...prev,
        currentVolume: response.currentVolume || 0,
        operatorsOnline: response.operatorsOnline || 0
      }));
    } catch (error) {
      console.error('Error loading real-time stats:', error);
    }
  };

  // Toggle real-time updates
  const toggleRealTime = () => {
    if (realTimeEnabled) {
      webSocketService.current.disconnect();
      setRealTimeEnabled(false);
      setRealTimeData([]);
      showSnackbar('Live updates disabled', 'info');
    } else {
      webSocketService.current.connect();
      setRealTimeEnabled(true);
      setRealTimeData([]);
      loadRealTimeStats(); // Load initial real-time stats
    }
  };

  // Handle filter changes
  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle refresh
  const handleRefresh = () => {
    if (realTimeEnabled) {
      loadRealTimeStats();
    } else {
      loadHistoricalData();
      loadOverallStats();
    }
  };

  // Calculate stats based on current view
  const getStats = () => {
    if (realTimeEnabled) {
      const recentData = realTimeData.slice(-10);
      return {
        ...overallStats,
        currentVolume: recentData.reduce((sum, day) => sum + (day.incoming || 0), 0),
        totalChats: realTimeData.reduce((sum, day) => sum + (day.incoming || 0), 0)
      };
    } else {
      return overallStats;
    }
  };

  const stats = getStats();

  // Format time for display
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Format hour for historical data
  const formatHour = (hour) => {
    return `${hour}:00`;
  };

  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2, border: '1px solid #ccc', minWidth: 200 }}>
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            {realTimeEnabled ? formatTime(label) : formatHour(label)}
          </Typography>
          {payload.map((entry, index) => (
            <Typography 
              key={index} 
              variant="body2" 
              sx={{ color: entry.color, display: 'flex', justifyContent: 'space-between' }}
            >
              <span>{entry.name}:</span>
              <span style={{ marginLeft: '10px', fontWeight: 'bold' }}>{entry.value}</span>
            </Typography>
          ))}
        </Paper>
      );
    }
    return null;
  };

  // Get data for chart based on current view
  const getChartData = () => {
    if (realTimeEnabled) {
      return realTimeData.map(point => ({
        ...point,
        time: point.timestamp,
        name: formatTime(point.timestamp)
      }));
    } else {
      return historicalData.map(point => ({
        ...point,
        time: point.hour,
        name: formatHour(point.hour)
      }));
    }
  };

  const chartData = getChartData();

  // Snackbar functions
  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  if (loading && historicalData.length === 0 && !realTimeEnabled) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading chat volume data...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h4" gutterBottom fontWeight="bold">
              Chat Volume
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {realTimeEnabled ? 'Live chat volume monitoring' : 'Historical chat volume analysis'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip
              icon={connectionStatus === 'connected' ? <Wifi /> : <WifiOff />}
              label={connectionStatus === 'connected' ? 'Live' : 'Offline'}
              color={connectionStatus === 'connected' ? 'success' : 'default'}
              variant="outlined"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={realTimeEnabled}
                  onChange={toggleRealTime}
                  color="primary"
                  disabled={connectionStatus === 'error'}
                />
              }
              label="Real-time"
            />
            <Tooltip title={realTimeEnabled ? "Pause updates" : "Start live updates"}>
              <IconButton 
                onClick={toggleRealTime}
                color={realTimeEnabled ? "primary" : "default"}
                disabled={connectionStatus === 'error'}
              >
                {realTimeEnabled ? <Pause /> : <PlayArrow />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {realTimeEnabled && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Live updates enabled. Data is updating in real-time.
            {connectionStatus === 'connected' && ' Connected to live data feed.'}
          </Alert>
        )}
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <ChatBubbleOutline color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold">
                    {stats.totalChats}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Chats
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <People color="success" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="success.main">
                    {stats.answeredChats}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Answered
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUp color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="warning.main">
                    {stats.missedChats}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Missed
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Schedule color="info" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="info.main">
                    {stats.avgResponseTime}s
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg Response
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUp color="secondary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="secondary.main">
                    {stats.currentVolume}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Current Volume
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <People color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold">
                    {stats.operatorsOnline}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Online Now
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                size="small"
                select
                value={filters.dateRange}
                onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                label="Time Range"
                disabled={realTimeEnabled}
              >
                {dateRangeOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                size="small"
                select
                value={filters.viewType}
                onChange={(e) => handleFilterChange('viewType', e.target.value)}
                label="View Type"
              >
                {viewTypeOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                {realTimeEnabled && connectionStatus === 'connected' && (
                  <LinearProgress 
                    sx={{ width: 100, my: 1 }} 
                    color="primary" 
                  />
                )}
                <Tooltip title="Refresh Data">
                  <IconButton onClick={handleRefresh} disabled={loading}>
                    <Refresh />
                  </IconButton>
                </Tooltip>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Main Chart */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {filters.viewType === 'volume' && 'Chat Volume Overview'}
            {filters.viewType === 'response' && 'Response Time Trend'}
            {filters.viewType === 'operators' && 'Operators Online'}
            {realTimeEnabled && ' (Live)'}
          </Typography>
          
          <Box sx={{ height: 300, mt: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              {filters.viewType === 'volume' ? (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name"
                    interval={realTimeEnabled ? 5 : 0}
                  />
                  <YAxis />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar 
                    dataKey="incoming" 
                    name="Incoming Chats" 
                    fill="#8884d8" 
                    radius={[2, 2, 0, 0]}
                  />
                  <Bar 
                    dataKey="answered" 
                    name="Answered Chats" 
                    fill="#82ca9d" 
                    radius={[2, 2, 0, 0]}
                  />
                  <Bar 
                    dataKey="missed" 
                    name="Missed Chats" 
                    fill="#ffc658" 
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              ) : filters.viewType === 'response' ? (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name"
                    interval={realTimeEnabled ? 5 : 0}
                  />
                  <YAxis label={{ value: 'Seconds', angle: -90, position: 'insideLeft' }} />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="responseTime" 
                    name="Response Time (s)" 
                    stroke="#ff7300" 
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              ) : (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name"
                    interval={realTimeEnabled ? 5 : 0}
                  />
                  <YAxis />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar 
                    dataKey="operatorsOnline" 
                    name="Operators Online" 
                    fill="#413ea0" 
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              )}
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>

      {/* Real-time Activity Feed */}
      {realTimeEnabled && realTimeData.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Live Activity Feed
            </Typography>
            <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
              {[...realTimeData].reverse().slice(0, 10).map((data, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    py: 1,
                    borderBottom: '1px solid',
                    borderColor: 'divider'
                  }}
                >
                  <Typography variant="body2">
                    {formatTime(data.timestamp)}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip 
                      label={`${data.incoming} incoming`} 
                      size="small" 
                      color="primary" 
                      variant="outlined"
                    />
                    <Chip 
                      label={`${data.answered} answered`} 
                      size="small" 
                      color="success" 
                      variant="outlined"
                    />
                    {data.missed > 0 && (
                      <Chip 
                        label={`${data.missed} missed`} 
                        size="small" 
                        color="error" 
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ChatVolume;
