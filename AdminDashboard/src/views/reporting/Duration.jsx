import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Material-UI Components
import {
  Grid,
  Card,
  CardContent,
  CardHeader,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Typography,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';

// Recharts
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

import { API_URL } from '../../config';

const Duration = () => {
  // State management
  const [dateRange, setDateRange] = useState('last7days');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [dailyStats, setDailyStats] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({
    total_sessions: 0,
    today_sessions: 0,
    today_visitors: 0,
    active_users_now: 0,
    avg_response_time: 0,
    total_messages: 0
  });
  const [chatSessions, setChatSessions] = useState([]);

  // Create axios instance with auth
  const createApi = useCallback(() => {
    const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
    return axios.create({
      baseURL: API_URL,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }, []);

  // Get date range parameters
  const getDateRangeParams = useCallback((range) => {
    const now = new Date();
    const start = new Date();

    switch (range) {
      case 'today':
        start.setHours(0, 0, 0, 0);
        return {
          start_date: start.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        };
      case 'yesterday':
        start.setDate(now.getDate() - 1);
        start.setHours(0, 0, 0, 0);
        now.setDate(now.getDate() - 1);
        now.setHours(23, 59, 59, 999);
        return {
          start_date: start.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        };
      case 'last7days':
        start.setDate(now.getDate() - 6);
        return {
          start_date: start.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        };
      case 'last30days':
        start.setDate(now.getDate() - 29);
        return {
          start_date: start.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        };
      default:
        start.setDate(now.getDate() - 6);
        return {
          start_date: start.toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        };
    }
  }, []);

  // Fetch all data
  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const api = createApi();
      const dateParams = getDateRangeParams(dateRange);

      console.log('📅 Fetching data with params:', dateParams);

      const [dailyResponse, dashboardResponse, sessionsResponse] = await Promise.all([
        api.get('/client/stats/daily', { params: dateParams }),
        api.get('/client/stats/dashboard'),
        api.get('/client/sessions/me')
      ]);

      console.log('✅ API Responses:', {
        daily: dailyResponse.data,
        dashboard: dashboardResponse.data,
        sessions: sessionsResponse.data
      });

      // Transform and set daily stats
      const transformed = transformDailyStats(dailyResponse.data.daily_stats || []);
      setDailyStats(transformed);

      // Set dashboard stats
      setDashboardStats(dashboardResponse.data);

      // Fetch session details
      await fetchSessionDetails(sessionsResponse.data.sessions || []);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch data';
      setError(errorMsg);
      console.error('❌ Error fetching data:', err);

      // Clear data on error
      setDailyStats([]);
      setChatSessions([]);
    } finally {
      setLoading(false);
    }
  }, [dateRange, createApi, getDateRangeParams]);

  // Load data on mount and when date range changes
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Transform daily stats for chart
  const transformDailyStats = (stats) => {
    if (!Array.isArray(stats) || stats.length === 0) {
      console.warn('No daily stats to transform');
      return [];
    }

    return stats
      .map((stat) => {
        const responseTime = stat.avg_response_time || 0;

        return {
          name: new Date(stat.date).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
          }),
          date: stat.date,
          visitors: stat.visitors || 0,
          chats: stat.chats || 0,
          responseTime: Math.round(responseTime * 100) / 100, // Round to 2 decimals
          responseTimeMin: Math.round((responseTime / 60) * 10) / 10 // Convert to minutes
        };
      })
      .filter((stat) => stat !== null);
  };

  // Fetch session details
  const fetchSessionDetails = async (sessions) => {
    if (!Array.isArray(sessions) || sessions.length === 0) {
      console.warn('No sessions to fetch details for');
      setChatSessions([]);
      return;
    }

    try {
      const api = createApi();

      // Limit to first 10 sessions for performance
      const sessionsToFetch = sessions.slice(0, 10);

      const sessionDetails = await Promise.all(
        sessionsToFetch.map(async (sessionId) => {
          try {
            const response = await api.get('/client/chats/me', {
              params: { session_id: sessionId }
            });

            return transformSessionData(sessionId, response.data);
          } catch (err) {
            console.error(`❌ Error fetching session ${sessionId}:`, err);
            return null;
          }
        })
      );

      // Filter out null sessions
      const validSessions = sessionDetails.filter((session) => session !== null);
      setChatSessions(validSessions);

      console.log(`✅ Loaded ${validSessions.length} sessions`);
    } catch (err) {
      console.error('❌ Error fetching session details:', err);
      setChatSessions([]);
    }
  };

  // Transform session data
  const transformSessionData = (sessionId, chatData) => {
    if (!chatData || !chatData.chats || !Array.isArray(chatData.chats) || chatData.chats.length === 0) {
      return null;
    }

    const chats = chatData.chats;
    const firstChat = chats[0];
    const lastChat = chats[chats.length - 1];

    // Calculate duration
    const startTime = new Date(firstChat.created_at);
    const endTime = new Date(lastChat.created_at);

    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      return null;
    }

    const durationMs = endTime - startTime;
    const durationMinutes = Math.max(0, Math.round(durationMs / (1000 * 60)));

    // Calculate average response time for this session
    const responseTimeChats = chats.filter(
      (chat) => chat.role === 'assistant' && chat.response_time !== null && chat.response_time !== undefined
    );

    const avgResponseTime =
      responseTimeChats.length > 0 ? responseTimeChats.reduce((sum, chat) => sum + chat.response_time, 0) / responseTimeChats.length : 0;

    return {
      id: sessionId,
      startTime: startTime.toLocaleString(),
      endTime: endTime.toLocaleString(),
      duration: `${durationMinutes} min`,
      durationValue: durationMinutes,
      messageCount: chats.length,
      avgResponseTime: Math.round(avgResponseTime * 100) / 100,
      status: durationMinutes === 0 ? 'Instant' : durationMinutes < 5 ? 'Short' : durationMinutes < 15 ? 'Normal' : 'Long',
      country: firstChat.country_code || 'Unknown'
    };
  };

  // Calculate overall stats from daily data
  const calculateOverallStats = () => {
    if (dailyStats.length === 0) {
      return {
        avgDuration: 0,
        minDuration: 0,
        maxDuration: 0,
        avgResponseTime: 0
      };
    }

    const durations = dailyStats.map((stat) => stat.responseTimeMin).filter((d) => d > 0);

    const responseTimes = dailyStats.map((stat) => stat.responseTime).filter((rt) => rt > 0);

    if (durations.length === 0) {
      return {
        avgDuration: 0,
        minDuration: 0,
        maxDuration: 0,
        avgResponseTime: 0
      };
    }

    return {
      avgDuration: Math.round((durations.reduce((a, b) => a + b, 0) / durations.length) * 10) / 10,
      minDuration: Math.min(...durations),
      maxDuration: Math.max(...durations),
      avgResponseTime:
        responseTimes.length > 0 ? Math.round((responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length) * 100) / 100 : 0
    };
  };

  const stats = calculateOverallStats();

  // Custom tooltip for chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          sx={{
            bgcolor: 'background.paper',
            p: 2,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            boxShadow: 3
          }}
        >
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2" sx={{ color: payload[0].color }} gutterBottom>
            Response Time: <strong>{data.responseTime}s</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Visitors: {data.visitors}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Messages: {data.chats}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  // Get status color
  const getStatusColor = (status) => {
    const colors = {
      Instant: 'success',
      Short: 'info',
      Normal: 'primary',
      Long: 'warning'
    };
    return colors[status] || 'default';
  };

  // Loading state
  if (loading && dailyStats.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading duration analytics...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          Chat Duration Analytics
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={fetchAllData}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filter and Stats Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Date Range</InputLabel>
                <Select value={dateRange} label="Date Range" onChange={(e) => setDateRange(e.target.value)}>
                  <MenuItem value="today">Today</MenuItem>
                  <MenuItem value="yesterday">Yesterday</MenuItem>
                  <MenuItem value="last7days">Last 7 Days</MenuItem>
                  <MenuItem value="last30days">Last 30 Days</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={8}>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <Typography variant="body2" color="text.secondary">
                  Total Sessions: <strong>{dashboardStats.total_sessions}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Today's Visitors: <strong>{dashboardStats.today_visitors}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Now: <strong>{dashboardStats.active_users_now}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Response: <strong>{dashboardStats.avg_response_time}s</strong>
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      {dailyStats.length > 0 && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#00C49F', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Min Duration
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {stats.minDuration} min
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Shortest conversation
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#0088FE', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Avg Duration
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {stats.avgDuration} min
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Average conversation
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#FF8042', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Max Duration
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {stats.maxDuration} min
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Longest conversation
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#8884d8', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Avg Response
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {stats.avgResponseTime}s
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  AI response time
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Chart */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Response Time Trend"
          subheader={
            dailyStats.length > 0 ? `Showing AI response times over ${dailyStats.length} days` : 'No data available for the selected period'
          }
        />
        <CardContent>
          {dailyStats.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyStats} margin={{ top: 20, right: 40, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" axisLine={true} tickLine={false} />
                <YAxis
                  axisLine={true}
                  tickLine={false}
                  label={{ value: 'Response Time (seconds)', angle: -90, position: 'insideLeft', offset: 10 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="responseTime"
                  name="Response Time"
                  stroke="#0088FE"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#0088FE' }}
                  activeDot={{ r: 6, fill: '#0088FE' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Box display="flex" justifyContent="center" alignItems="center" height={300} flexDirection="column">
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No data available
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Try selecting a different date range or check if data is being tracked
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Sessions Table */}
      <Card>
        <CardHeader
          title={`Recent Chat Sessions (${chatSessions.length})`}
          action={<Chip label={`${chatSessions.length} sessions`} color="primary" variant="outlined" />}
        />
        <CardContent>
          {chatSessions.length > 0 ? (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Session ID</TableCell>
                    <TableCell>Start Time</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Messages</TableCell>
                    <TableCell>Avg Response</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Country</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {chatSessions.map((session) => (
                    <TableRow key={session.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {session.id.substring(0, 12)}...
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.startTime}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          fontWeight="bold"
                          color={session.durationValue > 20 ? 'error.main' : session.durationValue < 5 ? 'success.main' : 'text.primary'}
                        >
                          {session.duration}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={session.messageCount} size="small" variant="outlined" color="primary" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.avgResponseTime}s</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={session.status} size="small" color={getStatusColor(session.status)} variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.country}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body1" color="text.secondary" align="center" py={4}>
              {loading ? 'Loading sessions...' : 'No chat sessions found for the selected period'}
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default Duration;
