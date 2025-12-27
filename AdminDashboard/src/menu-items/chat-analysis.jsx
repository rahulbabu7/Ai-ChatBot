import React from 'react';

const chatAnalysis = {
  id: 'chat-analysis',
  title: 'Chat Analysis',
  type: 'group',
  children: [
    {
      id: 'reporting',
      title: 'Reporting',
      type: 'collapse',
      icon: <i className="ph ph-lock-key" />,
      children: [
        {
          id: 'duration',
          title: 'Chat Duration',
          type: 'item',
          url: '/duration',
          breadcrumbs: false
        },
        {
          id: 'first-response-time',
          title: 'First Response Time',
          type: 'item',
          url: '/first-response-time',
          breadcrumbs: false
        }
      ]
    }
  ]
};

export default chatAnalysis;
