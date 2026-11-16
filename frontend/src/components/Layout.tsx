import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand">Transcript &amp; Credential Verifier</div>
        {user && (
          <nav>
            <Link to="/">Applicants</Link>
            <Link to="/equivalency-history">Equivalency History</Link>
          </nav>
        )}
        {user && (
          <div className="user-info">
            <span>{user.full_name} ({user.role})</span>
            <button onClick={handleLogout}>Log out</button>
          </div>
        )}
      </header>
      <main className="content">{children}</main>
    </div>
  );
}
