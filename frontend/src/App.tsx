import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ApplicantDetailPage from "./pages/ApplicantDetailPage";
import CredentialDetailPage from "./pages/CredentialDetailPage";
import EquivalencyHistoryPage from "./pages/EquivalencyHistoryPage";

function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/applicants/:id" element={<ApplicantDetailPage />} />
                <Route path="/credentials/:id" element={<CredentialDetailPage />} />
                <Route path="/equivalency-history" element={<EquivalencyHistoryPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
