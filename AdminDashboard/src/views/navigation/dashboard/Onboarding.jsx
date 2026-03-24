import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';

const STEPS = [
  {
    key: 'website_crawled',
    title: 'Crawl your website',
    description: 'Add your website URL so the chatbot can learn from your content.',
    action: 'Go to Setup',
    route: '/dashboard',
    icon: '🌐',
  },
  {
    key: 'pdf_uploaded',
    title: 'Upload a PDF document',
    description: 'Upload brochures, manuals, or any PDF to extend the knowledge base.',
    action: 'Go to Setup',
    route: '/dashboard',
    icon: '📄',
  },
  {
    key: 'qa_added',
    title: 'Add custom Q&A',
    description: 'Manually add question and answer pairs for common queries.',
    action: 'Go to Setup',
    route: '/dashboard',
    icon: '💬',
  },
  {
    key: 'chatbot_tested',
    title: 'Test your chatbot',
    description: 'Send at least one message to make sure the bot is responding correctly.',
    action: 'Go to Chat',
    route: '/',
    icon: '🧪',
  },
  {
    key: 'domain_configured',
    title: 'Configure your domain',
    description: 'Set the allowed domain and get your embed code to put the chatbot on your site.',
    action: 'Go to Domain',
    route: '/domain',
    icon: '🔗',
  },
];

export default function Onboarding() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${API_URL}/client/onboarding-status/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setStatus(res.data);
      } catch (err) {
        console.error('Failed to fetch onboarding status:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, [token]);

  if (loading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" />
        <p className="mt-2 text-muted">Loading setup progress...</p>
      </div>
    );
  }

  const steps = status?.steps || {};
  const completed = status?.completed || 0;
  const total = status?.total || STEPS.length;
  const percentage = status?.percentage || 0;
  const allDone = completed === total;

  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <h4 className="mb-1">
          {allDone ? '🎉 Setup Complete!' : 'Get Started'}
        </h4>
        <p className="text-muted mb-3">
          {allDone
            ? 'Your chatbot is fully configured and ready to serve your users.'
            : `Complete these steps to get your chatbot up and running. (${completed}/${total} done)`}
        </p>

        {/* Progress bar */}
        <div className="d-flex align-items-center gap-3 mb-1">
          <div className="progress flex-grow-1" style={{ height: '10px' }}>
            <div
              className={`progress-bar ${allDone ? 'bg-success' : 'bg-primary'}`}
              style={{ width: `${percentage}%`, transition: 'width 0.4s ease' }}
            />
          </div>
          <span className="fw-semibold text-nowrap">{percentage}%</span>
        </div>
      </div>

      {/* Steps */}
      <div className="d-flex flex-column gap-3">
        {STEPS.map((step, i) => {
          const done = steps[step.key] === true;
          return (
            <Card
              key={step.key}
              className={`shadow-sm border-2 ${done ? 'border-success' : 'border-light'}`}
              style={{ opacity: done ? 0.75 : 1 }}
            >
              <Card.Body className="d-flex align-items-center gap-3 py-3">
                {/* Status icon */}
                <div
                  className={`rounded-circle d-flex align-items-center justify-content-center flex-shrink-0 ${
                    done ? 'bg-success text-white' : 'bg-light text-muted'
                  }`}
                  style={{ width: 40, height: 40, fontSize: 18 }}
                >
                  {done ? '✓' : i + 1}
                </div>

                {/* Step info */}
                <div className="flex-grow-1">
                  <div className="d-flex align-items-center gap-2">
                    <span className="fs-5">{step.icon}</span>
                    <h6 className={`mb-0 ${done ? 'text-muted text-decoration-line-through' : ''}`}>
                      {step.title}
                    </h6>
                    {done && <span className="badge bg-success">Done</span>}
                  </div>
                  {!done && (
                    <p className="mb-0 small text-muted mt-1">{step.description}</p>
                  )}
                </div>

                {/* Action button */}
                {!done && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    className="flex-shrink-0"
                    onClick={() => navigate(step.route)}
                  >
                    {step.action} →
                  </Button>
                )}
              </Card.Body>
            </Card>
          );
        })}
      </div>

      {/* Footer CTA */}
      {allDone && (
        <Card className="mt-4 bg-success text-white border-0 shadow-sm">
          <Card.Body className="text-center py-4">
            <h5 className="mb-2">Your chatbot is live!</h5>
            <p className="mb-3 opacity-75">
              Check the Analytics page to see how users are interacting with it.
            </p>
            <Button variant="light" onClick={() => navigate('/analytics')}>
              View Analytics
            </Button>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}
