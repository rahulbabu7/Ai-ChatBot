import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Dropdown from 'react-bootstrap/Dropdown';
import Image from 'react-bootstrap/Image';
import Nav from 'react-bootstrap/Nav';
import Stack from 'react-bootstrap/Stack';
import { handlerDrawerOpen, useGetMenuMaster } from 'api/menu';
import Img2 from 'assets/images/user/avatar-2.png';
import { API_URL } from '../../config';

export default function Header() {
  const navigate = useNavigate();
  const { menuMaster } = useGetMenuMaster();
  const drawerOpen = menuMaster?.isDashboardDrawerOpened;

  const [user, setUser] = useState({ name: '', email: '' });

  useEffect(() => {
    const fetchUserDetails = async () => {
      try {
        // Try to get token from localStorage first, then sessionStorage
        const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
        if (!token) return;

        const res = await fetch(`${API_URL}/auth/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          } // matches backend
        });
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
    localStorage.removeItem('jwt_token');
    sessionStorage.removeItem('jwt_token');
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
                <Dropdown.Item as={Link} to="#" className="justify-content-start">
                  <i className="ph ph-gear me-2" /> Settings
                </Dropdown.Item>
                <Dropdown.Item as={Link} to="#" className="justify-content-start">
                  <i className="ph ph-share-network me-2" /> Share
                </Dropdown.Item>
                <Dropdown.Item as={Link} to="#" className="justify-content-start">
                  <i className="ph ph-lock-key me-2" /> Change Password
                </Dropdown.Item>
                <Dropdown.Divider />
                <Dropdown.Item as="button" className="justify-content-start" onClick={handleLogout}>
                  <i className="ph ph-sign-out me-2" /> Logout
                </Dropdown.Item>
              </div>
            </Dropdown.Menu>
          </Dropdown>
        </Nav>
      </div>
    </header>
  );
}
