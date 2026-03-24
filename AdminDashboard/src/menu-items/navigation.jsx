import React from 'react';

const icons = {
  dashboard: <i className="ph ph-house-line" />,
  layouts: <i className="ph ph-layout" />
};

// Navigation routes
const navigation = {
  id: 'group-dashboard-loading-unique',
  title: 'Navigation',
  type: 'group',
  icon: icons.dashboard,
  children: [
    // client items
    { id: 'dashboard', title: 'Dashboard', type: 'item', icon: icons.dashboard, url: '/', roles: ['client'] },
    { id: 'onboarding', title: 'Get Started', type: 'item', icon: <i className="ph ph-rocket-launch" />, url: '/onboarding', roles: ['client'] },
    { id: 'analytics', title: 'Analytics', type: 'item', icon: <i className="ph ph-chart-bar" />, url: '/analytics', roles: ['client'] },
    { id: 'dashboard-client', title: 'Setup', type: 'item', icon: icons.layouts, url: '/dashboard', roles: ['client'] },
    { id: 'domain', title: 'Domain', type: 'item', icon: icons.layouts, url: '/domain', roles: ['client'] },
    { id: 'leads', title: 'Leads', type: 'item', icon: icons.layouts, url: '/leads', roles: ['client'] },
    { id: 'duration', title: 'Chat Duration', type: 'item', icon: <i className="ph ph-timer" />, url: '/duration', roles: ['client'] },
    { id: 'first-response-time', title: 'First Response Time', type: 'item', icon: <i className="ph ph-clock" />, url: '/first-response-time', roles: ['client'] },
  ]
};

export default navigation;
