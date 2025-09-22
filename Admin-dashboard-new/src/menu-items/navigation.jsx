import React from 'react';

const icons = {
  dashboard: <i className="ph ph-house-line" />,
  layouts: <i className="ph ph-layout" />
};

// Get latest logged-in clientId from storage
const getLatestClientId = () => {
  const localClientKeys = Object.keys(localStorage).filter(k => k.startsWith('clientId_'));
  const sessionClientKeys = Object.keys(sessionStorage).filter(k => k.startsWith('clientId_'));

  const allClientIds = [...localClientKeys, ...sessionClientKeys].map(key => {
    return localStorage.getItem(key) || sessionStorage.getItem(key);
  });

  if (allClientIds.length === 0) return null;

  return allClientIds[allClientIds.length - 1]; // latest client
};

const clientId = getLatestClientId();

const navigation = {
  id: 'group-dashboard-loading-unique',
  title: 'Navigation',
  type: 'group',
  icon: icons.dashboard,
  children: [
    { id: 'dashboard', title: 'Dashboard', type: 'item', icon: icons.dashboard, url: '/' },
    {
      id: 'dashboard-client',
      title: 'Dashboard Client',
      type: 'item',
      icon: icons.layouts,
      url: clientId ? `/client/${clientId}` : '/login' // ✅ fixed template literal
    },
    { id: 'domain', title: 'Domain', type: 'item', icon: icons.layouts, url: '/domain' }
  ]
};

export default navigation;
