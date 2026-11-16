import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import apiClient from "../api/client";
import type { Credential, EquivalencyQuery, Paginated } from "../types";

export default function CredentialDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [credential, setCredential] = useState<Credential | null>(null);
  const [history, setHistory] = useState<EquivalencyQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    const credentialResp = await apiClient.get<Credential>(`/credentials/${id}/`);
    setCredential(credentialResp.data);
    const historyResp = await apiClient.get<Paginated<EquivalencyQuery>>("/equivalency-queries/");
    setHistory(historyResp.data.results.filter((q) => q.credential === Number(id)));
    setLoading(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setAsking(true);
    try {
      await apiClient.post("/equivalency-queries/", {
        credential: Number(id),
        question_text: question,
      });
      setQuestion("");
      await load();
    } catch {
      setError("Could not submit the question.");
    } finally {
      setAsking(false);
    }
  };

  if (loading || !credential) return <p className="loading">Loading...</p>;

  return (
    <div>
      <Link to={`/applicants/${credential.applicant}`}>&larr; {credential.applicant_name}</Link>
      <h1>{credential.institution}</h1>
      <p className="muted">
        {credential.credential_type} &middot;{" "}
        <span className={`badge badge-${credential.status}`}>{credential.status}</span>
      </p>

      <h2>Extracted course records</h2>
      {credential.records.length === 0 ? (
        <p className="muted">No records yet. Process this credential first.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Course / Subject</th>
              <th>Grade / Score</th>
              <th>Term</th>
            </tr>
          </thead>
          <tbody>
            {credential.records.map((record) => (
              <tr key={record.id}>
                <td>{record.course_or_subject}</td>
                <td>{record.grade_or_score}</td>
                <td>{record.term}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="card" onSubmit={handleAsk}>
        <h2>Ask an equivalency question</h2>
        <label>
          Question
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g. "Does this transcript cover material equivalent to our CS301 course?"'
            required
          />
        </label>
        <button type="submit" disabled={asking || credential.status !== "processed"}>
          {asking ? "Asking..." : "Ask"}
        </button>
        {credential.status !== "processed" && (
          <p className="muted">Process this credential before asking equivalency questions.</p>
        )}
        {error && <p className="error">{error}</p>}
      </form>

      <h2>Equivalency question history for this credential</h2>
      {history.length === 0 ? (
        <p className="muted">No questions asked yet.</p>
      ) : (
        <ul className="history-list">
          {history.map((item) => (
            <li key={item.id} className="card">
              <p className="question">{item.question_text}</p>
              <p className="answer">{item.answer_text}</p>
              <p className="meta">
                {item.reviewer_email} &middot; {new Date(item.created_at).toLocaleString()} &middot;{" "}
                {item.retrieved_chunk_ids.length} chunk(s) cited
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
