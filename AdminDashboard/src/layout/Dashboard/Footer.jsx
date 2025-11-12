// react-bootstrap
import Col from 'react-bootstrap/Col';
import Nav from 'react-bootstrap/Nav';
import Row from 'react-bootstrap/Row';
import Stack from 'react-bootstrap/Stack';

// project-imports
import branding from 'branding.json';

// ==============================|| MAIN LAYOUT - FOOTER ||============================== //
export default function Footer() {
  return (
    <footer className="pc-footer">
      <div className="footer-wrapper  container-fluid">
        <Row className="justify-content-center justify-content-md-between">
          {/* Footer Text */}
          <Col xs="auto" className="my-1">
            <p className="m-0">
              {branding.brandName} ♥ Crafted By Team{' at '}
              <a href="https://kochi.digital/" target="_blank" rel="noopener noreferrer" className="text-primary">
                Kochi.Digital
              </a>
            </p>
          </Col>

          {/* Footer Links */}
          <Col xs="auto" className="my-1">
            <Stack direction="horizontal" gap={3} className="justify-content-center">
              <Nav.Link className="p-0" as="a" href="/">
                Home
              </Nav.Link>
              <Nav.Link className="p-0" as="a" href="https://kochi.digital/contact.html" target="_blank" rel="noopener noreferrer">
                Documentation
              </Nav.Link>
              <Nav.Link className="p-0" as="a" href="https://kochi.digital/contact.html" target="_blank" rel="noopener noreferrer">
                Support
              </Nav.Link>
            </Stack>
          </Col>
        </Row>
      </div>
    </footer>
  );
}
