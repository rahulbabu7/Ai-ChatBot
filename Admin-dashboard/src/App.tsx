// src/App.tsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import AdminDashboard from "./pages/AdminDashboard.tsx";
import ClientManager from "./pages/ClientManager.tsx";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AdminDashboard />} />
        <Route path="/client/:clientId" element={<ClientManager />} />
      </Routes>
    </Router>
  );
}

export default App;
