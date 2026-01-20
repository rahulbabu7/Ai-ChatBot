import { useLocation } from 'react-router-dom';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import navigation from 'menu-items';

export default function Breadcrumbs() {
  const location = useLocation();
  
  // Get current page title
  const getPageTitle = () => {
    let pageTitle = '';
    
    const findTitle = (items) => {
      for (const item of items) {
        if (item.type === 'item' && item.url === location.pathname) {
          return item.title || '';
        }
        if (item.children) {
          const found = findTitle(item.children);
          if (found) return found;
        }
      }
      return '';
    };
    
  };
  
  const pageTitle = getPageTitle();
  
  return (
    <div className="page-header">
      <div className="page-block">
        <Row className="align-items-center">
          <Col md={12} className="page-header-title text-capitalize">
            <h5>{pageTitle}</h5>
          </Col>
          {/* Removed breadcrumb Col completely */}
        </Row>
      </div>
    </div>
  );
}
