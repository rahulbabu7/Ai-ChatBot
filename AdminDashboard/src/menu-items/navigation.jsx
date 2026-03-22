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
    { id: 'dashboard', title: 'Dashboard', type: 'item', icon: icons.dashboard, url: '/' },
    { id: 'onboarding', title: 'Get Started', type: 'item', icon: <i className="ph ph-rocket-launch" />, url: '/onboarding' },
    { id: 'analytics', title: 'Analytics', type: 'item', icon: <i className="ph ph-chart-bar" />, url: '/analytics' },
    { id: 'dashboard-client', title: 'Setup', type: 'item', icon: icons.layouts, url: '/dashboard' },
    { id: 'domain', title: 'Domain', type: 'item', icon: icons.layouts, url: '/domain' },
    { id: 'leads', title: 'Leads', type: 'item', icon: icons.layouts, url: '/leads' },
  ]
};

export default navigation;
