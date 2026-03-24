import PropTypes from 'prop-types';
import { useState } from 'react';

// react-bootstrap
import ListGroup from 'react-bootstrap/ListGroup';

// project-imports
import NavItem from './NavItem';
import NavGroup from './NavGroup';
import menuItems from 'menu-items';

// ==============================|| NAVIGATION ||============================== //

function filterByRole(items, role) {
  return items
    .filter((item) => !item.roles || item.roles.includes(role))
    .map((item) => ({
      ...item,
      ...(item.children ? { children: filterByRole(item.children, role) } : {})
    }));
}

export default function Navigation({ selectedItems, setSelectedItems, setSelectTab }) {
  const [selectedID, setSelectedID] = useState('');
  const [selectedLevel, setSelectedLevel] = useState(0);

  const userRole = localStorage.getItem('user_role') || 'client';

  const filteredItems = {
    ...menuItems,
    items: menuItems.items.map((group) => ({
      ...group,
      children: group.children ? filterByRole(group.children, userRole) : group.children
    }))
  };

  const lastItem = null;
  let lastItemIndex = filteredItems.items.length - 1;
  let remItems = [];
  let lastItemId;

  if (lastItem && lastItem < filteredItems.items.length) {
    lastItemId = filteredItems.items[lastItem - 1].id;
    lastItemIndex = lastItem - 1;
    remItems = filteredItems.items.slice(lastItem - 1, filteredItems.items.length).map((item) => ({
      id: item.id,
      type: item.type,
      title: item.title,
      elements: item.children,
      icon: item.icon,
      ...(item.url && {
        url: item.url
      })
    }));
  }

  const navGroups = filteredItems.items.slice(0, lastItemIndex + 1).map((item, index) => {
    switch (item.type) {
      case 'group':
        if (item.url && item.id !== lastItemId) {
          return (
            <>
              <ListGroup.Item key={index}>
                <NavItem item={item} level={1} isParents />
              </ListGroup.Item>
            </>
          );
        }

        return (
          <NavGroup
            key={item.id}
            setSelectedID={setSelectedID}
            setSelectedItems={setSelectedItems}
            setSelectedLevel={setSelectedLevel}
            selectedLevel={selectedLevel}
            selectedID={selectedID}
            selectedItems={selectedItems}
            lastItem={lastItem}
            remItems={remItems}
            lastItemId={lastItemId}
            item={item}
            setSelectTab={setSelectTab ?? (() => {})}
          />

        );
      default:
        return (
          <h6 key={item.id} color="error" className="align-items-center">
            Fix - Navigation Group
          </h6>
        );
    }
  });

  return <ul className={`pc-navbar 'd-block'`}>{navGroups}</ul>;
}

Navigation.propTypes = {
  selectedItems: PropTypes.any,
  setSelectedItems: PropTypes.oneOfType([PropTypes.func, PropTypes.any]),
  setSelectTab: PropTypes.oneOfType([PropTypes.func, PropTypes.any])
};
