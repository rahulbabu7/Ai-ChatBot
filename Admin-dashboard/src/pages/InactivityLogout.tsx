import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const InactivityLogout = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    let timer: NodeJS.Timeout;

    // Skip inactivity logout if user is on login or signup page
    if (location.pathname === "/login" || location.pathname === "/signup") {
      return;
    }

    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        localStorage.removeItem("client_id");
        sessionStorage.removeItem("client_id");
        navigate("/login"); // Redirect to login
      }, 900000); // 15 minutes
    };

    // Monitor mousemove and keydown events for activity
    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);

    // Start the inactivity timer
    resetTimer();

    // Clean up the event listeners when component unmounts
    return () => {
      window.removeEventListener("mousemove", resetTimer);
      window.removeEventListener("keydown", resetTimer);
      clearTimeout(timer);
    };
  }, [navigate, location]);

  return null; // No UI, just handles inactivity logic in the background
};

export default InactivityLogout;
