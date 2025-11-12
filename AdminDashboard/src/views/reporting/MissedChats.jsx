// src/views/reporting/MissedChats.jsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Avatar,
  TextField,
  MenuItem,
  IconButton,
  Tooltip,
  Pagination,
  Button,
  Snackbar,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  FilterList,
  Refresh,
  Visibility,
  MailOutline,
  ChatBubbleOutline,
  AccessTime,
  CheckCircle,
  Cancel
} from '@mui/icons-material';

// API service functions
const missedChatsAPI = {
  // Fetch missed chats with filters
  getMissedChats: async (filters = {}) => {
    const queryParams = new URLSearchParams();
    
    if (filters.status && filters.status !== 'all') {
      queryParams.append('status', filters.status);
    }
    if (filters.operator && filters.operator !== 'all') {
      queryParams.append('operator', filters.operator);
    }
    if (filters.dateRange) {
      queryParams.append('dateRange', filters.dateRange);
    }
    if (filters.search) {
      queryParams.append('search', filters.search);
    }
    if (filters.page) {
      queryParams.append('page', filters.page);
    }
    if (filters.limit) {
      queryParams.append('limit', filters.limit);
    }

    const response = await fetch(`/api/missed-chats?${queryParams}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch missed chats');
    }
    
    return await response.json();
  },

  // Update chat status
  updateChatStatus: async (chatId, status) => {
    const response = await fetch(`/api/missed-chats/${chatId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status }),
    });

    if (!response.ok) {
      throw new Error('Failed to update chat status');
    }

    return await response.json();
  },

  // Send follow-up email
  sendFollowUp: async (chatId, message) => {
    const response = await fetch(`/api/missed-chats/${chatId}/follow-up`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error('Failed to send follow-up');
    }

    return await response.json();
  },

  // Get available operators
  getOperators: async () => {
    const response = await fetch('/api/operators');
    
    if (!response.ok) {
      throw new Error('Failed to fetch operators');
    }
    
    return await response.json();
  }
};

const MissedChats = () => {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [operators, setOperators] = useState([]);
  const [filters, setFilters] = useState({
    status: 'all',
    operator: 'all',
    dateRange: '7days'
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [actionLoading, setActionLoading] = useState(null);
  const rowsPerPage = 10;

  // Status configuration
  const statusConfig = {
    missed: { color: 'error', label: 'Missed', icon: <Cancel /> },
    pending: { color: 'warning', label: 'Pending', icon: <AccessTime /> },
    resolved: { color: 'success', label: 'Resolved', icon: <CheckCircle /> }
  };

  // Load initial data
  useEffect(() => {
    loadData();
    loadOperators();
  }, []);

  // Load data when filters or page change
  useEffect(() => {
    loadData();
  }, [filters, page, searchTerm]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const apiFilters = {
        ...filters,
        search: searchTerm,
        page: page,
        limit: rowsPerPage
      };

      const response = await missedChatsAPI.getMissedChats(apiFilters);
      
      setData(response.data || []);
      setFilteredData(response.data || []);
      setTotalCount(response.totalCount || 0);
    } catch (error) {
      console.error('Error loading missed chats:', error);
      showSnackbar('Failed to load missed chats', 'error');
      setData([]);
      setFilteredData([]);
    } finally {
      setLoading(false);
    }
  };

  const loadOperators = async () => {
    try {
      const response = await missedChatsAPI.getOperators();
      setOperators(response.data || []);
    } catch (error) {
      console.error('Error loading operators:', error);
      setOperators([]);
    }
  };

  // Handle filter changes
  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
    setPage(1); // Reset to first page when filters change
  };

  // Handle refresh
  const handleRefresh = () => {
    loadData();
    loadOperators();
  };

  // Handle status update
  const handleStatusUpdate = async (chatId, newStatus) => {
    try {
      setActionLoading(chatId);
      await missedChatsAPI.updateChatStatus(chatId, newStatus);
      showSnackbar('Status updated successfully', 'success');
      loadData(); // Refresh data
    } catch (error) {
      console.error('Error updating status:', error);
      showSnackbar('Failed to update status', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle follow up
  const handleFollowUp = async (chat) => {
    try {
      setActionLoading(chat.id);
      await missedChatsAPI.sendFollowUp(chat.id, `Follow-up for chat with ${chat.visitor.name}`);
      showSnackbar('Follow-up sent successfully', 'success');
    } catch (error) {
      console.error('Error sending follow-up:', error);
      showSnackbar('Failed to send follow-up', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle view details
  const handleViewDetails = (chat) => {
    // Navigate to chat details page or open modal
    console.log('View details:', chat);
    // You can implement navigation or modal opening here
  };

  // Handle send email
  const handleSendEmail = (chat) => {
    // Open email client or modal
    const subject = `Follow up: Chat from ${chat.visitor.name}`;
    const body = `Hello ${chat.visitor.name},\n\nRegarding our chat on ${new Date(chat.date).toLocaleDateString()}...`;
    window.open(`mailto:${chat.visitor.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
  };

  // Snackbar functions
  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  // Calculate stats from data
  const stats = {
    total: totalCount,
    missed: data.filter(item => item.status === 'missed').length,
    pending: data.filter(item => item.status === 'pending').length,
    resolved: data.filter(item => item.status === 'resolved').length
  };

  if (loading && data.length === 0) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading missed chats...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight="bold">
          Missed Chats
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Monitor and manage missed chat conversations
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <ChatBubbleOutline color="primary" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold">
                    {stats.total}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Chats
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Cancel color="error" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="error.main">
                    {stats.missed}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Missed Chats
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AccessTime color="warning" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="warning.main">
                    {stats.pending}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pending Chats
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CheckCircle color="success" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" fontWeight="bold" color="success.main">
                    {stats.resolved}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Resolved Chats
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
            <Grid item xs={12} md={5}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search visitors, operators..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: <FilterList sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            </Grid>
            <Grid item xs={6} md={3}>
              <TextField
                fullWidth
                size="small"
                select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                label="Status"
              >
                <MenuItem value="all">All Status</MenuItem>
                <MenuItem value="missed">Missed</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="resolved">Resolved</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={6} md={3}>
              <TextField
                fullWidth
                size="small"
                select
                value={filters.operator}
                onChange={(e) => handleFilterChange('operator', e.target.value)}
                label="Operator"
              >
                <MenuItem value="all">All Operators</MenuItem>
                {operators.map(operator => (
                  <MenuItem key={operator.id} value={operator.id}>
                    {operator.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={1}>
              <Tooltip title="Refresh">
                <IconButton onClick={handleRefresh} disabled={loading}>
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><strong>Visitor</strong></TableCell>
                <TableCell><strong>Operator</strong></TableCell>
                <TableCell><strong>Date & Time</strong></TableCell>
                <TableCell><strong>Duration</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredData.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      No missed chats found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredData.map((chat) => (
                  <TableRow key={chat.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                          {chat.visitor?.name?.charAt(0) || 'V'}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {chat.visitor?.name || 'Unknown Visitor'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {chat.visitor?.email || 'No email'}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {chat.operator?.name || chat.operatorId || 'Unassigned'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {new Date(chat.date).toLocaleDateString()}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(chat.date).toLocaleTimeString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {chat.duration || 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={statusConfig[chat.status]?.icon}
                        label={statusConfig[chat.status]?.label || chat.status}
                        color={statusConfig[chat.status]?.color || 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="View Details">
                          <IconButton 
                            size="small" 
                            color="primary"
                            onClick={() => handleViewDetails(chat)}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Send Email">
                          <IconButton 
                            size="small" 
                            color="secondary"
                            onClick={() => handleSendEmail(chat)}
                            disabled={!chat.visitor?.email}
                          >
                            <MailOutline />
                          </IconButton>
                        </Tooltip>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<ChatBubbleOutline />}
                          onClick={() => handleFollowUp(chat)}
                          disabled={actionLoading === chat.id}
                        >
                          {actionLoading === chat.id ? <CircularProgress size={16} /> : 'Follow Up'}
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Showing {filteredData.length} of {totalCount} chats
          </Typography>
          <Pagination
            count={Math.ceil(totalCount / rowsPerPage)}
            page={page}
            onChange={(e, value) => setPage(value)}
            color="primary"
          />
        </Box>
      </Card>

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

export default MissedChats;
