import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import apiClient from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Applicant, Credential, CredentialType, Paginated } from "../types";

export default function ApplicantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [applicant, setApplicant] = useState<Applicant | null>(null);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);

  const [institution, setInstitution] = useState("");
  const [credentialType, setCredentialType] = useState<CredentialType>("transcript");
  const [issueDate, setIssueDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    const [applicantResp, credentialsResp] = await Promise.all([
      apiClient.get<Applicant>(`/applicants/${id}/`),
      apiClient.get<Paginated<Credential>>(`/credentials/?applicant=${id}`),
    ]);
    setApplicant(applicantResp.data);
    setCredentials(credentialsResp.data.results);
    setLoading(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!file) {
      setError("Choose a document file to upload.");
      return;
    }
    const formData = new FormData();
    formData.append("applicant", id!);
    formData.append("institution", institution);
    formData.append("credential_type", credentialType);
    if (issueDate) formData.append("issue_date", issueDate);
    formData.append("file", file);

    try {
      await apiClient.post("/credentials/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setInstitution("");
      setIssueDate("");
      setFile(null);
      load();
    } catch {
      setError("Upload failed. Check the required fields.");
    }
  };

  const handleProcess = async (credentialId: number) => {
    setProcessingId(credentialId);
    try {
      await apiClient.post(`/credentials/${credentialId}/process/`);
      await load();
    } finally {
      setProcessingId(null);
    }
  };

  const handleDelete = async (credentialId: number) => {
    if (!window.confirm("Delete this credential?")) return;
    await apiClient.delete(`/credentials/${credentialId}/`);
    load();
  };

  if (loading || !applicant) return <p className="loading">Loading...</p>;

  return (
    <div>
      <Link to="/">&larr; All applicants</Link>
      <h1>{applicant.full_name}</h1>
      <p className="muted">{applicant.email}</p>

      <form className="card" onSubmit={handleUpload}>
        <h2>Upload a credential document</h2>
        <div className="form-row">
          <label>
            Institution
            <input value={institution} onChange={(e) => setInstitution(e.target.value)} required />
          </label>
          <label>
            Type
            <select value={credentialType} onChange={(e) => setCredentialType(e.target.value as CredentialType)}>
              <option value="transcript">Transcript</option>
              <option value="certificate">Certificate</option>
              <option value="diploma">Diploma</option>
            </select>
          </label>
          <label>
            Issue date
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label>
            Document file (plain text, one course per line: "Course | Grade | Term")
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <button type="submit">Upload</button>
        </div>
        {error && <p className="error">{error}</p>}
      </form>

      <h2>Credentials</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Institution</th>
            <th>Type</th>
            <th>Status</th>
            <th>Courses</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {credentials.map((credential) => (
            <tr key={credential.id}>
              <td>{credential.institution}</td>
              <td>{credential.credential_type}</td>
              <td>
                <span className={`badge badge-${credential.status}`}>{credential.status}</span>
              </td>
              <td>{credential.records.length}</td>
              <td className="actions">
                <Link to={`/credentials/${credential.id}`}>View</Link>
                {credential.status === "uploaded" && (
                  <button
                    onClick={() => handleProcess(credential.id)}
                    disabled={processingId === credential.id}
                  >
                    {processingId === credential.id ? "Processing..." : "Process"}
                  </button>
                )}
                {user?.role === "admin" && (
                  <button className="danger" onClick={() => handleDelete(credential.id)}>
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {credentials.length === 0 && <p className="muted">No credentials uploaded yet.</p>}
    </div>
  );
}
