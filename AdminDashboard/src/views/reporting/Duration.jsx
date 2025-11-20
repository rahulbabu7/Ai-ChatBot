import React, { useState, useEffect } from 'react';

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

// Recharts for charts
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

// API service - make sure this is properly configured
import apiService from 'services/apiService';

const Duration = () => {
  // State for filters
  const [dateRange, setDateRange] = useState('last7days');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Real data states
  const [dailyStats, setDailyStats] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({
    total_sessions: 0,
    today_sessions: 0,
    today_visitors: 0,
    active_users_now: 0
  });
  const [chatSessions, setChatSessions] = useState([]);

  // Fetch all data on component mount and when dateRange changes
  useEffect(() => {
    fetchAllData();
  }, [dateRange]);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get date range parameters for API calls
      const dateParams = getDateRangeParams(dateRange);
      
      const [dailyResponse, dashboardResponse, sessionsResponse] = await Promise.all([
        apiService.get('/client/stats/daily', { params: dateParams }),
        apiService.get('/client/stats/dashboard'),
        apiService.get('/client/sessions/me', { params: dateParams })
      ]);

      console.log('Raw API Responses:', {
        daily: dailyResponse,
        dashboard: dashboardResponse,
        sessions: sessionsResponse
      });

      // Transform daily stats for line chart - using ONLY REAL data
      const transformedDailyStats = transformDailyStats(dailyResponse);
      setDailyStats(transformedDailyStats);
      
      // Set dashboard stats
      setDashboardStats(dashboardResponse);
      
      // Fetch detailed session data
      await fetchSessionDetails(sessionsResponse);

    } catch (err) {
      const errorMessage = err.response?.data?.message || 'Failed to fetch data from server. Please check your connection and try again.';
      setError(errorMessage);
      console.error('Error fetching data:', err);
      
      // Set empty states - NO FALLBACK DATA
      setDailyStats([]);
      setChatSessions([]);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get date range parameters
  const getDateRangeParams = (range) => {
    const now = new Date();
    const startDate = new Date();
    
    switch (range) {
      case 'today':
        startDate.setHours(0, 0, 0, 0);
        break;
      case 'yesterday':
        startDate.setDate(now.getDate() - 1);
        startDate.setHours(0, 0, 0, 0);
        const yesterdayEnd = new Date(startDate);
        yesterdayEnd.setHours(23, 59, 59, 999);
        return {
          start_date: startDate.toISOString(),
          end_date: yesterdayEnd.toISOString()
        };
      case 'last7days':
        startDate.setDate(now.getDate() - 7);
        break;
      case 'last30days':
        startDate.setDate(now.getDate() - 30);
        break;
      default:
        startDate.setDate(now.getDate() - 7);
    }
    
    return {
      start_date: startDate.toISOString(),
      end_date: now.toISOString()
    };
  };

  // Transform daily stats from API response - NO FAKE DATA
  const transformDailyStats = (dailyResponse) => {
    // Check if we have the expected data structure
    if (!dailyResponse || !dailyResponse.daily_stats || !Array.isArray(dailyResponse.daily_stats)) {
      console.warn('No daily_stats found in response:', dailyResponse);
      return [];
    }

    const validStats = dailyResponse.daily_stats.filter(stat => {
      // Only include stats that have real duration data
      const hasDurationData = 
        (stat.shortest_duration !== undefined && stat.shortest_duration !== null) ||
        (stat.average_duration !== undefined && stat.average_duration !== null) ||
        (stat.longest_duration !== undefined && stat.longest_duration !== null);
      
      if (!hasDurationData) {
        console.warn('Skipping stat due to missing duration data:', stat);
      }
      
      return hasDurationData;
    });

    if (validStats.length === 0) {
      console.warn('No valid daily stats with duration data found');
      return [];
    }

    return validStats.map(stat => {
      // Use ONLY actual duration data from API
      // If any duration field is missing, skip the stat or use null
      const shortest = stat.shortest_duration !== undefined ? stat.shortest_duration / 60 : null; // Convert to minutes
      const longest = stat.longest_duration !== undefined ? stat.longest_duration / 60 : null; // Convert to minutes
      const average = stat.average_duration !== undefined ? stat.average_duration / 60 : null; // Convert to minutes

      // If any required duration is missing, return null (will be filtered out)
      if (shortest === null || average === null || longest === null) {
        console.warn('Incomplete duration data for stat:', stat);
        return null;
      }

      return {
        name: new Date(stat.date).toLocaleDateString('en-US', { 
          weekday: 'short', 
          month: 'short', 
          day: 'numeric' 
        }),
        date: stat.date,
        visitors: stat.visitors || stat.unique_visitors || 0,
        chats: stat.chats || stat.total_chats || 0,
        shortest: Math.round(shortest * 10) / 10,
        average: Math.round(average * 10) / 10,
        longest: Math.round(longest * 10) / 10
      };
    }).filter(stat => stat !== null);
  };

  // Fetch detailed session data
  const fetchSessionDetails = async (sessionsResponse) => {
    if (!sessionsResponse || !sessionsResponse.sessions || !Array.isArray(sessionsResponse.sessions)) {
      console.warn('No sessions found in response:', sessionsResponse);
      setChatSessions([]);
      return;
    }

    try {
      // Limit to first 10 sessions for performance
      const sessionsToFetch = sessionsResponse.sessions.slice(0, 10);
      
      const sessionDetails = await Promise.all(
        sessionsToFetch.map(async (session) => {
          try {
            // Use session ID from the session object or the object itself
            const sessionId = session.id || session.session_id || session;
            
            const chatResponse = await apiService.get('/client/chats/me', {
              params: { session_id: sessionId }
            });
            
            return transformSessionData(sessionId, chatResponse, session);
          } catch (err) {
            console.error(`Error fetching details for session:`, err);
            return null; // Return null instead of fake data
          }
        })
      );

      // Filter out null sessions and sessions without real data
      const validSessions = sessionDetails.filter(session => 
        session !== null && 
        session.duration !== 'N/A' && 
        session.startTime !== 'N/A'
      );
      
      setChatSessions(validSessions);
    } catch (err) {
      console.error('Error fetching session details:', err);
      setChatSessions([]);
    }
  };

  // Transform session data from API response - NO FAKE DATA
  const transformSessionData = (sessionId, chatResponse, originalSession) => {
    // Try to get data from original session first
    if (originalSession) {
      const hasValidData = 
        originalSession.start_time && 
        originalSession.duration !== undefined && 
        originalSession.duration !== null;
      
      if (hasValidData) {
        return {
          id: sessionId,
          startTime: new Date(originalSession.start_time).toLocaleString(),
          endTime: originalSession.end_time ? new Date(originalSession.end_time).toLocaleString() : 'N/A',
          duration: formatDuration(originalSession.duration),
          status: originalSession.status || 'Unknown',
          satisfaction: originalSession.satisfaction_score !== undefined ? originalSession.satisfaction_score : 'N/A',
          messageCount: originalSession.message_count || 0
        };
      }
    }

    // Otherwise, try to calculate from chat data
    if (!chatResponse || !chatResponse.chats || !Array.isArray(chatResponse.chats)) {
      console.warn('No chat data available for session:', sessionId);
      return null;
    }

    const chats = chatResponse.chats;
    if (chats.length === 0) {
      console.warn('Empty chat array for session:', sessionId);
      return null;
    }

    const userMessages = chats.filter(chat => chat.role === 'user');
    if (userMessages.length === 0) {
      console.warn('No user messages in session:', sessionId);
      return null;
    }

    const firstMessage = userMessages[0];
    const lastMessage = chats[chats.length - 1];

    // Calculate duration based on timestamps - REAL DATA
    const startTime = new Date(firstMessage.created_at || firstMessage.timestamp);
    const endTime = new Date(lastMessage.created_at || lastMessage.timestamp);
    
    // Validate dates
    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      console.warn('Invalid timestamps for session:', sessionId);
      return null;
    }

    const durationMs = endTime - startTime;
    const durationMinutes = Math.max(1, Math.round(durationMs / (1000 * 60)));

    return {
      id: sessionId,
      startTime: startTime.toLocaleString(),
      endTime: endTime.toLocaleString(),
      duration: `${durationMinutes} min`,
      status: 'Calculated', // Indicate this was calculated, not from API
      satisfaction: 'N/A', // No fake satisfaction scores
      messageCount: chats.length
    };
  };

  // Format duration from seconds to minutes
  const formatDuration = (durationInSeconds) => {
    if (durationInSeconds === undefined || durationInSeconds === null) {
      return 'N/A';
    }
    const minutes = Math.round(durationInSeconds / 60);
    return `${minutes} min`;
  };

  // Handler for View All Sessions button
  const handleViewAllSessions = async () => {
    setLoading(true);
    try {
      const dateParams = getDateRangeParams(dateRange);
      const sessionsResponse = await apiService.get('/client/sessions/me', { 
        params: { ...dateParams, limit: 50 } // Increase limit for "view all"
      });
      
      await fetchSessionDetails(sessionsResponse);
      
    } catch (err) {
      setError('Failed to fetch all sessions. Please try again.');
      console.error('Error fetching all sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateOverallStats = () => {
    if (dailyStats.length === 0) {
      return {
        averageDuration: 0,
        longestDuration: 0,
        shortestDuration: 0
      };
    }

    const allShortest = dailyStats.map(stat => stat.shortest).filter(d => d > 0);
    const allAverage = dailyStats.map(stat => stat.average).filter(d => d > 0);
    const allLongest = dailyStats.map(stat => stat.longest).filter(d => d > 0);

    if (allShortest.length === 0) {
      return {
        averageDuration: 0,
        longestDuration: 0,
        shortestDuration: 0
      };
    }

    const average = Math.round(allAverage.reduce((a, b) => a + b, 0) / allAverage.length * 10) / 10;
    const longest = Math.max(...allLongest);
    const shortest = Math.min(...allShortest);

    return {
      averageDuration: average,
      longestDuration: longest,
      shortestDuration: shortest
    };
  };

  const stats = calculateOverallStats();

  // Custom tooltip for the line chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box sx={{ 
          bgcolor: 'background.paper', 
          p: 2, 
          border: 1, 
          borderColor: 'divider', 
          borderRadius: 1,
          boxShadow: 3
        }}>
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            {label}
          </Typography>
          {payload.map((entry, index) => (
            <Typography 
              key={index} 
              variant="body2" 
              sx={{ color: entry.color }}
              gutterBottom
            >
              {entry.name}: <strong>{entry.value} min</strong>
            </Typography>
          ))}
          <Typography variant="body2" color="text.secondary">
            Visitors: {data.visitors || 0}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Chats: {data.chats || 0}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  const getStatusColor = (status) => {
    const statusColors = {
      'Resolved': 'success',
      'Pending': 'warning',
      'Closed': 'error',
      'Active': 'info',
      'Calculated': 'info'
    };
    return statusColors[status] || 'default';
  };

  if (loading && chatSessions.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading chat duration analytics...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header Section with Title and Refresh Button */}
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

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Debug information - remove in production */}
      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2">
          Data Status: {dailyStats.length} daily stats, {chatSessions.length} sessions
        </Typography>
      </Alert>

      {/* Filter and Stats Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Date Range</InputLabel>
                <Select
                  value={dateRange}
                  label="Date Range"
                  onChange={(e) => setDateRange(e.target.value)}
                >
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
                  Total Sessions: <strong>{dashboardStats.total_sessions || 0}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Today's Visitors: <strong>{dashboardStats.today_visitors || 0}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Now: <strong>{dashboardStats.active_users_now || 0}</strong>
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Duration Stats Cards - Only show if we have real data */}
      {dailyStats.length > 0 && (
        <Grid container spacing={5} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#00C49F', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h7" gutterBottom>Shortest Duration</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.shortestDuration} min</Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Based on {dailyStats.length} days of real data
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#0088FE', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h7" gutterBottom>Average Duration</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.averageDuration} min</Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Based on {dailyStats.length} days of real data
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#FF8042', color: 'white', height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h7" gutterBottom>Longest Duration</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.longestDuration} min</Typography>
                <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                  Based on {dailyStats.length} days of real data
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Chart Section - Only show if we have real data */}
      <Card sx={{ mb: 3 }}>
        <CardHeader 
          title="Daily Chat Duration Analysis" 
          subheader={dailyStats.length > 0 
            ? "Showing shortest, average, and longest chat durations over time" 
            : "No duration data available for the selected period"
          }
        />
        <CardContent>
          {dailyStats.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={dailyStats}
                margin={{ top: 20, right: 40, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  axisLine={true}
                  tickLine={false}
                />
                <YAxis 
                  axisLine={true}
                  tickLine={false}
                  label={{ 
                    value: 'Duration (minutes)', 
                    angle: -90, 
                    position: 'insideLeft',
                    offset: 10 
                  }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                
                <Line
                  type="monotone"
                  dataKey="shortest"
                  name="Shortest Duration"
                  stroke="#00C49F"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#00C49F' }}
                  activeDot={{ r: 6, fill: '#00C49F' }}
                />
                
                <Line
                  type="monotone"
                  dataKey="average"
                  name="Average Duration"
                  stroke="#0088FE"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#0088FE' }}
                  activeDot={{ r: 6, fill: '#0088FE' }}
                />
                
                <Line
                  type="monotone"
                  dataKey="longest"
                  name="Longest Duration"
                  stroke="#FF8042"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#FF8042' }}
                  activeDot={{ r: 6, fill: '#FF8042' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Box display="flex" justifyContent="center" alignItems="center" height={300} flexDirection="column">
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No duration data available
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Check if your backend API is providing duration data in the expected format
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Recent Chat Sessions Table */}
      <Card>
        <CardHeader 
          title="Recent Chat Sessions" 
          action={
            <Button 
              variant="outlined" 
              size="small"
              onClick={handleViewAllSessions}
              disabled={loading}
            >
              View All Sessions
            </Button>
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
                    <TableCell>End Time</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Messages</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Satisfaction</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {chatSessions.map((session) => (
                    <TableRow key={session.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {session.id.substring(0, 12)}...
                        </Typography>
                      </TableCell>
                      <TableCell>{session.startTime}</TableCell>
                      <TableCell>{session.endTime}</TableCell>
                      <TableCell>
                        <Typography 
                          variant="body2" 
                          fontWeight="bold"
                          color={
                            parseInt(session.duration) > 20 ? 'error' :
                            parseInt(session.duration) < 10 ? 'success' : 'text.primary'
                          }
                        >
                          {session.duration}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={session.messageCount} 
                          size="small"
                          variant="outlined"
                        />
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
                        {session.satisfaction !== 'N/A' ? (
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {[...Array(5)].map((_, i) => (
                              <Box
                                key={i}
                                sx={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: '50%',
                                  bgcolor: i < session.satisfaction ? 'gold' : 'grey.300',
                                  mr: 0.5
                                }}
                              />
                            ))}
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            N/A
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body1" color="text.secondary" align="center" py={4}>
              No chat sessions found with real data for the selected period.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default Duration;
