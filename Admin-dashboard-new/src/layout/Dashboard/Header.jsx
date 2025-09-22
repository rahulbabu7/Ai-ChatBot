import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Dropdown from 'react-bootstrap/Dropdown';
import Image from 'react-bootstrap/Image';
import Nav from 'react-bootstrap/Nav';
import Stack from 'react-bootstrap/Stack';
import { handlerDrawerOpen, useGetMenuMaster } from 'api/menu';
import Img2 from 'assets/images/user/avatar-2.png';

export default function Header() {
  const navigate = useNavigate();
  const { menuMaster } = useGetMenuMaster();
  const drawerOpen = menuMaster?.isDashboardDrawerOpened;

  const [user, setUser] = useState({ name: '', email: '' });

  useEffect(() => {
    const fetchUserDetails = async () => {
      try {
        // Get all clientId keys from localStorage and sessionStorage
        const localClientKeys = Object.keys(localStorage).filter(k => k.startsWith('clientId_'));
        const sessionClientKeys = Object.keys(sessionStorage).filter(k => k.startsWith('clientId_'));
  
        const allClientKeys = [...localClientKeys, ...sessionClientKeys];
        if (allClientKeys.length === 0) return;
  
        // Pick the last added key
        const latestKey = allClientKeys[allClientKeys.length - 1];
        const clientId =
          localStorage.getItem(latestKey) || sessionStorage.getItem(latestKey);
  
        if (!clientId) return;
  
        const res = await fetch(`http://localhost:8000/client/${clientId}`);
        if (!res.ok) throw new Error('Failed to fetch user details');
  
        const data = await res.json();
        setUser({ name: data.name, email: data.email });
      } catch (error) {
        console.error('Error fetching user details:', error);
      }
    };
  
    fetchUserDetails();
  }, []);

  const handleLogout = () => {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('clientId_') || key.startsWith('chatbotKey_')) localStorage.removeItem(key);
    });
    Object.keys(sessionStorage).forEach(key => {
      if (key.startsWith('clientId_') || key.startsWith('chatbotKey_')) sessionStorage.removeItem(key);
    });
    localStorage.removeItem('token');
    navigate('/login', { replace: true });
  };

  return (
    <header className="pc-header">
      <div className="header-wrapper d-flex align-items-center justify-content-between">
        <Nav className="list-unstyled d-flex align-items-center">
          <Nav.Item className="pc-h-item pc-sidebar-collapse">
            <Nav.Link as={Link} to="#" className="pc-head-link ms-0" onClick={() => handlerDrawerOpen(!drawerOpen)}>
              <i className="ph ph-list" />
            </Nav.Link>
          </Nav.Item>
        </Nav>

        <Nav className="list-unstyled d-flex align-items-center ms-auto">
          <Dropdown align="end">
            <Dropdown.Toggle className="pc-head-link p-0 border-0 bg-transparent" variant="link" id="user-dropdown">
              <Image src={Img2} alt="user-avatar" style={{ width: '35px', height: '35px', cursor: 'pointer' }} roundedCircle />
            </Dropdown.Toggle>

            <Dropdown.Menu className="dropdown-user-profile pc-h-dropdown p-0 overflow-hidden">
              <Dropdown.Header className="bg-primary">
                <Stack direction="horizontal" gap={2} className="my-2 align-items-center">
                  <Image src={Img2} alt="user-avatar" style={{ width: '35px', height: '35px' }} roundedCircle />
                  <div>
                    <h6 className="text-white mb-0">{user.name || 'Loading...'}</h6>
                    <span className="text-white text-opacity-75">{user.email || ''}</span>
                  </div>
                </Stack>
              </Dropdown.Header>

              <div className="dropdown-body p-2">
                <Dropdown.Item as={Link} to="#" className="justify-content-start"><i className="ph ph-gear me-2" /> Settings</Dropdown.Item>
                <Dropdown.Item as={Link} to="#" className="justify-content-start"><i className="ph ph-share-network me-2" /> Share</Dropdown.Item>
                <Dropdown.Item as={Link} to="#" className="justify-content-start"><i className="ph ph-lock-key me-2" /> Change Password</Dropdown.Item>
                <Dropdown.Divider />
                <Dropdown.Item as="button" className="justify-content-start" onClick={handleLogout}><i className="ph ph-sign-out me-2" /> Logout</Dropdown.Item>
              </div>
            </Dropdown.Menu>
          </Dropdown>
        </Nav>
      </div>
    </header>
  );
}
