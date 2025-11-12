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
    { id: 'dashboard-client', title: 'Dashboard Client', type: 'item', icon: icons.layouts, url: '/dashboard' },
    { id: 'domain', title: 'Domain', type: 'item', icon: icons.layouts, url: '/domain' }
  ]
};

export default navigation;
