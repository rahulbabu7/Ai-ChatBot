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
          id: 'chat-volume',
          title: 'Chat Volume',
          type: 'item',
          url: '/chat-volume',
          breadcrumbs: false
        },
        {
          id: 'missed-chats',
          title: 'Missed Chats',
          type: 'item',
          url: '/missed-chats',
          breadcrumbs: false
        }
      ]
    }
  ]
};

export default chatAnalysis;
