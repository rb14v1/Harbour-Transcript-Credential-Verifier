import { useEffect, useState } from "react";
import apiClient from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { EquivalencyQuery, Paginated } from "../types";

export default function EquivalencyHistoryPage() {
  const { user } = useAuth();
  const [history, setHistory] = useState<EquivalencyQuery[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get<Paginated<EquivalencyQuery>>("/equivalency-queries/").then((resp) => {
      setHistory(resp.data.results);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <h1>Equivalency question history</h1>
      <p className="muted">
        {user?.role === "admin"
          ? "Showing every reviewer's questions (admin view)."
          : "Showing your own questions."}
      </p>

      {loading ? (
        <p className="loading">Loading...</p>
      ) : history.length === 0 ? (
        <p className="muted">No equivalency questions have been asked yet.</p>
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
