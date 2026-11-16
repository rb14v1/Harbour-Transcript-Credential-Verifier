import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Applicant, Paginated } from "../types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [loading, setLoading] = useState(true);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadApplicants = async () => {
    setLoading(true);
    const response = await apiClient.get<Paginated<Applicant>>("/applicants/");
    setApplicants(response.data.results);
    setLoading(false);
  };

  useEffect(() => {
    loadApplicants();
  }, []);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await apiClient.post("/applicants/", { full_name: fullName, email });
      setFullName("");
      setEmail("");
      loadApplicants();
    } catch {
      setError("Could not create applicant. Check the email is unique.");
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this applicant and all their credentials?")) return;
    await apiClient.delete(`/applicants/${id}/`);
    loadApplicants();
  };

  return (
    <div>
      <h1>Applicants</h1>

      <form className="card inline-form" onSubmit={handleCreate}>
        <h2>Add applicant</h2>
        <div className="form-row">
          <label>
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <button type="submit">Add</button>
        </div>
        {error && <p className="error">{error}</p>}
      </form>

      {loading ? (
        <p className="loading">Loading applicants...</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Credentials</th>
              <th>Added</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {applicants.map((applicant) => (
              <tr key={applicant.id}>
                <td>
                  <Link to={`/applicants/${applicant.id}`}>{applicant.full_name}</Link>
                </td>
                <td>{applicant.email}</td>
                <td>{applicant.credential_count}</td>
                <td>{new Date(applicant.created_at).toLocaleDateString()}</td>
                <td>
                  {user?.role === "admin" && (
                    <button className="danger" onClick={() => handleDelete(applicant.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
