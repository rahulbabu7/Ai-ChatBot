import { Link } from "react-router-dom";

const AdminDashboard = () => {
  const clients = ["abc_college", "xyz_college"]; // Later fetch from backend

  return (
    <div>
      <h2>Admin Dashboard</h2>
      <ul>
        {clients.map((c) => (
          <li key={c}>
            <Link to={`/client/${c}`}>{c}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AdminDashboard;
