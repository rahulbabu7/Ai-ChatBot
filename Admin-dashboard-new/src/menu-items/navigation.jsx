const icons = { 
  dashboard: <i className="ph ph-house-line" />, 
  layouts: <i className="ph ph-layout" /> 
};

const navigation = {
  id: 'group-dashboard-loading-unique',
  title: 'Navigation',
  type: 'group',
  icon: icons.dashboard,
  children: [
    {
      id: 'dashboard',
      title: 'Dashboard',
      type: 'item',
      icon: icons.dashboard,
      url: '/'
    },
    {
      id: 'dashboard-admin',
      title: 'Dashboard Admin',
      type: 'item',
      icon: icons.layouts,
      url: '/dashboard-admin'
    },
    {
      id: 'dashboard-client',
      title: 'Dashboard Client',
      type: 'item',
      icon: icons.layouts,
      url: '/dashboard-client'
    }
  ]
};

export default navigation;
