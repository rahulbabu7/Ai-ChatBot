// UserSatisfaction.jsx - Pure API Fetch Version
import React, { useState, useEffect } from 'react';

const UserSatisfaction = () => {
    const [loading, setLoading] = useState(false);
    const [feedbackData, setFeedbackData] = useState([]);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        const fetchFeedbackData = async () => {
            setLoading(true);
            setError(null);
            
            try {
                // Replace with your actual API endpoint
                const response = await fetch('https://api.example.com/feedback', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        // Add authentication headers if needed
                        // 'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
                }
                
                const data = await response.json();
                setFeedbackData(data);
            } catch (err) {
                setError(err.message);
                console.error('Error fetching feedback data:', err);
            } finally {
                setLoading(false);
            }
        };
        
        fetchFeedbackData();
    }, []);
    
    const handleRefresh = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('https://api.example.com/feedback');
            
            if (!response.ok) {
                throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            setFeedbackData(data);
        } catch (err) {
            setError(err.message);
            console.error('Error refreshing data:', err);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="container-fluid">
            <div className="row">
                <div className="col-12">
                    <div className="d-flex justify-content-between align-items-center mt-4 mb-4">
                        <h1>User Satisfaction Dashboard</h1>
                        <button 
                            className="btn btn-primary"
                            onClick={handleRefresh}
                            disabled={loading}
                        >
                            {loading ? (
                                <span>
                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                    Refreshing...
                                </span>
                            ) : (
                                <span>
                                    <i className="fas fa-sync-alt me-2"></i>
                                    Refresh Data
                                </span>
                            )}
                        </button>
                    </div>
                    
                    {error && (
                        <div className="alert alert-danger alert-dismissible fade show" role="alert">
                            <strong>Error:</strong> {error}
                            <button type="button" className="btn-close" onClick={() => setError(null)}></button>
                        </div>
                    )}
                    
                    <div className="card">
                        <div className="card-header d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">Feedback Summary</h5>
                            <span className="badge bg-primary">
                                Total: {feedbackData.length} entries
                            </span>
                        </div>
                        <div className="card-body">
                            {loading && feedbackData.length === 0 ? (
                                <div className="text-center py-5">
                                    <div className="spinner-border text-primary" style={{width: '3rem', height: '3rem'}}></div>
                                    <p className="mt-3">Loading feedback data...</p>
                                </div>
                            ) : error && feedbackData.length === 0 ? (
                                <div className="text-center py-5">
                                    <i className="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                                    <p className="text-danger">Failed to load data. Please try again.</p>
                                    <button className="btn btn-primary mt-2" onClick={handleRefresh}>
                                        Retry
                                    </button>
                                </div>
                            ) : feedbackData.length === 0 ? (
                                <div className="text-center py-5">
                                    <i className="fas fa-inbox fa-3x text-muted mb-3"></i>
                                    <p className="text-muted">No feedback data available</p>
                                </div>
                            ) : (
                                <div className="table-responsive">
                                    <table className="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Rating</th>
                                                <th>User</th>
                                                <th>Comment</th>
                                                <th>Date</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {feedbackData.map(item => (
                                                <tr key={item.id}>
                                                    <td>{item.id}</td>
                                                    <td>
                                                        <div className="d-flex align-items-center">
                                                            {[...Array(5)].map((_, i) => (
                                                                <i 
                                                                    key={i}
                                                                    className={`fas fa-star ${i < item.rating ? 'text-warning' : 'text-light'}`}
                                                                ></i>
                                                            ))}
                                                            <span className="ms-2">({item.rating}/5)</span>
                                                        </div>
                                                    </td>
                                                    <td>{item.user}</td>
                                                    <td>{item.comment}</td>
                                                    <td>{new Date(item.date).toLocaleDateString()}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                        <div className="card-footer">
                            <small className="text-muted">
                                Last updated: {new Date().toLocaleTimeString()}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UserSatisfaction;
