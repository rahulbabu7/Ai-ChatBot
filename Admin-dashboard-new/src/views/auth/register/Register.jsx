// project-imports
import AuthRegister from "sections/auth/AuthRegister";

// ===========================|| AUTH - REGISTER PAGE ||=========================== //

export default function RegisterPage() {
  return (
    <div className="auth-main">
      <div className="auth-wrapper v1">
        <div className="auth-form">
          <div className="position-relative">
            <div className="auth-bg">
              <span className="r"></span>
              <span className="r s"></span>
              <span className="r s"></span>
              <span className="r"></span>
            </div>
            {/* Render the new functional signup form */}
            <AuthRegister link="/login" />
          </div>
        </div>
      </div>
    </div>
  );
}
