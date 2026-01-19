import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

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
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import { Refresh as RefreshIcon, Chat as ChatIcon } from '@mui/icons-material';

// Recharts
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend, ResponsiveContainer } from 'recharts';

import { API_URL } from '../../config';

const Duration = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  
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
  const [sessionStats, setSessionStats] = useState({
    total_sessions: 0,
    avg_duration_minutes: 0,
    min_duration_minutes: 0,
    max_duration_minutes: 0,
    total_messages: 0,
    avg_messages_per_session: 0,
    avg_response_time: 0
  });
  const [chatSessions, setChatSessions] = useState([]);
  const [sessionDurations, setSessionDurations] = useState({});

  // Create axios instance with auth
  const createApi = useCallback(() => {
    return axios.create({
      baseURL: API_URL,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }, [token]);

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

      const [dailyResponse, dashboardResponse, sessionStatsResponse, sessionsResponse] = await Promise.all([
        api.get('/client/stats/daily', { params: dateParams }),
        api.get('/client/stats/dashboard'),
        api.get('/client/stats/sessions', { params: dateParams }), // NEW: Get aggregated session stats
        api.get('/client/sessions/me')
      ]);

      console.log('✅ API Responses:', {
        daily: dailyResponse.data,
        dashboard: dashboardResponse.data,
        sessionStats: sessionStatsResponse.data,
        sessions: sessionsResponse.data
      });

      // Transform and set daily stats
      const transformed = transformDailyStats(dailyResponse.data.daily_stats || []);
      setDailyStats(transformed);

      // Set dashboard stats
      setDashboardStats(dashboardResponse.data);
      
      // Set session stats (filtered by date range)
      setSessionStats(sessionStatsResponse.data);

      // Fetch session details and durations, then filter by date range
      await fetchSessionDetails(sessionsResponse.data.sessions || [], dateParams);
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
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
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
          name: new Date(stat.date).toLocaleDateString('en-IN', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            timeZone: 'Asia/Kolkata'
          }),
          date: stat.date,
          visitors: stat.visitors || 0,
          chats: stat.chats || 0,
          responseTime: Math.round(responseTime * 100) / 100,
          responseTimeMin: Math.round((responseTime / 60) * 10) / 10
        };
      })
      .filter((stat) => stat !== null);
  };

  // Fetch session details and durations
  const fetchSessionDetails = async (sessions) => {
    if (!Array.isArray(sessions) || sessions.length === 0) {
      console.warn('No sessions to fetch details for');
      setChatSessions([]);
      return;
    }

    try {
      const api = createApi();

      // Limit to first 20 sessions for performance
      const sessionsToFetch = sessions.slice(0, 20);

      const sessionDetails = await Promise.all(
        sessionsToFetch.map(async (sessionId) => {
          try {
            // Fetch chat history
            const chatResponse = await api.get('/client/chats/me', {
              params: { session_id: sessionId }
            });

            // Fetch session duration
            let durationData = null;
            try {
              const durationResponse = await api.get(`/client/session-duration/${sessionId}`);
              durationData = durationResponse.data;
              
              // Store duration in state
              setSessionDurations(prev => ({
                ...prev,
                [sessionId]: durationData
              }));
            } catch (durationErr) {
              console.warn(`⚠️ No duration data for session ${sessionId}`);
            }

            return transformSessionData(sessionId, chatResponse.data, durationData);
          } catch (err) {
            console.error(`❌ Error fetching session ${sessionId}:`, err);
            return null;
          }
        })
      );

      // Filter out null sessions
      const validSessions = sessionDetails.filter((session) => session !== null);
      setChatSessions(validSessions);

      console.log(`✅ Loaded ${validSessions.length} sessions with duration data`);
    } catch (err) {
      console.error('❌ Error fetching session details:', err);
      setChatSessions([]);
    }
  };

  // Transform session data with duration
  const transformSessionData = (sessionId, chatData, durationData) => {
    if (!chatData || !chatData.chats || !Array.isArray(chatData.chats) || chatData.chats.length === 0) {
      return null;
    }

    const chats = chatData.chats;
    const firstChat = chats[0];
    const lastChat = chats[chats.length - 1];

    // Calculate message-based duration (time between first and last message)
    const startTime = new Date(firstChat.created_at);
    const endTime = new Date(lastChat.created_at);

    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      return null;
    }

    const messageDurationMs = endTime - startTime;
    const messageDurationMinutes = Math.max(0, Math.round(messageDurationMs / (1000 * 60)));

    // Use actual session duration if available (time chatbot was open)
    let actualDuration = messageDurationMinutes;
    let isLive = false;
    
    if (durationData) {
      actualDuration = durationData.duration_minutes || messageDurationMinutes;
      isLive = durationData.is_active || false;
    }

    // Calculate average response time for this session
    const responseTimeChats = chats.filter(
      (chat) => chat.role === 'assistant' && chat.response_time !== null && chat.response_time !== undefined
    );

    const avgResponseTime =
      responseTimeChats.length > 0 
        ? responseTimeChats.reduce((sum, chat) => sum + chat.response_time, 0) / responseTimeChats.length 
        : 0;

    return {
      id: sessionId,
      startTime: startTime.toLocaleString('en-IN', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata'
      }),
      endTime: endTime.toLocaleString('en-IN', {
        day: 'numeric', 
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata'
      }),
      duration: `${Math.round(actualDuration)} min`,
      durationValue: Math.round(actualDuration),
      messageDuration: `${messageDurationMinutes} min`,
      messageCount: chats.length,
      avgResponseTime: Math.round(avgResponseTime * 100) / 100,
      status: actualDuration === 0 ? 'Instant' : actualDuration < 5 ? 'Short' : actualDuration < 15 ? 'Normal' : 'Long',
      country: firstChat.country_code || 'Unknown',
      isLive: isLive
    };
  };

  // Calculate overall stats from SESSION data (not daily stats)
  const calculateOverallStats = () => {
    // Use actual session durations from chatSessions, not daily response times
    if (chatSessions.length === 0) {
      return {
        avgDuration: 0,
        minDuration: 0,
        maxDuration: 0,
        avgResponseTime: 0,
        totalSessions: 0
      };
    }

    // Get all session durations (in minutes)
    const sessionDurations = chatSessions.map((s) => s.durationValue).filter((d) => d > 0);
    
    // Get all session response times (in seconds)
    const sessionResponseTimes = chatSessions.map((s) => s.avgResponseTime).filter((rt) => rt > 0);

    // If no valid durations, return zeros
    if (sessionDurations.length === 0) {
      return {
        avgDuration: 0,
        minDuration: 0,
        maxDuration: 0,
        avgResponseTime: sessionResponseTimes.length > 0 
          ? Math.round((sessionResponseTimes.reduce((a, b) => a + b, 0) / sessionResponseTimes.length) * 100) / 100 
          : 0,
        totalSessions: chatSessions.length
      };
    }

    return {
      avgDuration: Math.round((sessionDurations.reduce((a, b) => a + b, 0) / sessionDurations.length) * 10) / 10,
      minDuration: Math.min(...sessionDurations),
      maxDuration: Math.max(...sessionDurations),
      avgResponseTime:
        sessionResponseTimes.length > 0 
          ? Math.round((sessionResponseTimes.reduce((a, b) => a + b, 0) / sessionResponseTimes.length) * 100) / 100 
          : 0,
      totalSessions: chatSessions.length
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

  // Navigate to admin chat
  const handleOpenChat = (sessionId) => {
    console.log('🔍 Opening admin chat for session:', sessionId);
    navigate(`/client-chat/${sessionId}`);
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
          📊 Chat Duration Analytics
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={fetchAllData}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
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

      {/* Dynamic Stats Cards based on filter - NOW USES sessionStats */}
      {sessionStats.total_sessions > 0 ? (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {/* Card 1: Total Sessions */}
          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#00C49F', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  {dateRange === 'today' ? "Today's Sessions" : 
                   dateRange === 'yesterday' ? "Yesterday's Sessions" : 
                   dateRange === 'last7days' ? "This Week" : 
                   "This Month"}
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {sessionStats.total_sessions}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  {dateRange === 'today' ? "Active today" : 
                   dateRange === 'yesterday' ? "Total yesterday" : 
                   dateRange === 'last7days' ? "Last 7 days" : 
                   "Last 30 days"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Card 2: Average Duration */}
          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#0088FE', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  Avg Duration
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {Math.round(sessionStats.avg_duration_minutes)} min
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  {dateRange === 'today' ? "Average today" : 
                   dateRange === 'yesterday' ? "Average yesterday" : 
                   dateRange === 'last7days' ? "7-day average" : 
                   "30-day average"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Card 3: Peak Duration */}
          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#FF8042', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  {dateRange === 'today' || dateRange === 'yesterday' ? "Longest Session" : "Peak Duration"}
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {Math.round(sessionStats.max_duration_minutes)} min
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  {dateRange === 'today' ? "Best today" : 
                   dateRange === 'yesterday' ? "Best yesterday" : 
                   dateRange === 'last7days' ? "Weekly peak" : 
                   "Monthly peak"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Card 4: Total Messages or Response Time */}
          <Grid item xs={12} md={3}>
            <Card sx={{ bgcolor: '#8884d8', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  {dateRange === 'today' || dateRange === 'yesterday' ? "Avg Response" : "Total Messages"}
                </Typography>
                <Typography variant="h4" fontWeight="bold">
                  {dateRange === 'today' || dateRange === 'yesterday' 
                    ? `${sessionStats.avg_response_time}s` 
                    : sessionStats.total_messages}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  {dateRange === 'today' ? "AI speed today" : 
                   dateRange === 'yesterday' ? "AI speed yesterday" : 
                   dateRange === 'last7days' ? "Last 7 days" : 
                   "Last 30 days"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Alert severity="info" sx={{ mb: 3 }}>
          📊 No sessions found for the selected date range. Try selecting "Last 7 Days" or "Last 30 Days" to see data.
        </Alert>
      )}

      {/* Chart */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Response Time Trend"
          subheader={
            dailyStats.length > 0 
              ? `Showing AI response times over ${dailyStats.length} days` 
              : 'No data available for the selected period'
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
                <ChartTooltip content={<CustomTooltip />} />
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
          action={
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip 
                label={`${chatSessions.filter(s => s.isLive).length} LIVE`} 
                color="success" 
                size="small"
                sx={{ animation: chatSessions.filter(s => s.isLive).length > 0 ? 'pulse 2s infinite' : 'none' }}
              />
              <Chip label={`${chatSessions.length} total`} color="primary" variant="outlined" size="small" />
            </Box>
          }
        />
        <CardContent>
          {chatSessions.length > 0 ? (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Session ID</TableCell>
                    <TableCell>Start Time</TableCell>
                    <TableCell>Session Duration</TableCell>
                    <TableCell>Msg Duration</TableCell>
                    <TableCell>Messages</TableCell>
                    <TableCell>Avg Response</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Country</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {chatSessions.map((session) => (
                    <TableRow 
                      key={session.id} 
                      hover
                      sx={{
                        bgcolor: session.isLive ? 'rgba(76, 175, 80, 0.05)' : 'inherit'
                      }}
                    >
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {session.isLive && (
                            <Chip 
                              label="LIVE" 
                              color="success" 
                              size="small" 
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          )}
                          <Typography variant="body2" fontFamily="monospace">
                            {session.id.substring(0, 12)}...
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.startTime}</Typography>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Time chatbot window was open">
                          <Typography
                            variant="body2"
                            fontWeight="bold"
                            color={
                              session.durationValue > 20 
                                ? 'error.main' 
                                : session.durationValue < 5 
                                  ? 'success.main' 
                                  : 'text.primary'
                            }
                          >
                            ⏱️ {session.duration}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Time between first and last message">
                          <Typography variant="body2" color="text.secondary">
                            💬 {session.messageDuration}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Chip label={session.messageCount} size="small" variant="outlined" color="primary" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.avgResponseTime}s</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={session.status} 
                          size="small" 
                          color={getStatusColor(session.status)} 
                          variant="outlined" 
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.country}</Typography>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Open admin chat">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleOpenChat(session.id)}
                          >
                            <ChatIcon />
                          </IconButton>
                        </Tooltip>
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

      {/* Add pulse animation */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}
      </style>
    </Box>
  );
};

export default Duration;