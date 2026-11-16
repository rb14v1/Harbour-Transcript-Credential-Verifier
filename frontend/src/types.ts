export type Role = "admissions_reviewer" | "admin";

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
}

export interface Applicant {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
  credential_count: number;
}

export type CredentialType = "transcript" | "certificate" | "diploma";
export type CredentialStatus = "uploaded" | "processed";

export interface CredentialRecord {
  id: number;
  credential: number;
  course_or_subject: string;
  grade_or_score: string;
  term: string;
}

export interface Credential {
  id: number;
  applicant: number;
  applicant_name: string;
  institution: string;
  credential_type: CredentialType;
  blob_path: string;
  issue_date: string | null;
  status: CredentialStatus;
  uploaded_by: number | null;
  created_at: string;
  records: CredentialRecord[];
  chunk_count: number;
}

export interface EquivalencyQuery {
  id: number;
  reviewer: number;
  reviewer_email: string;
  credential: number | null;
  question_text: string;
  answer_text: string;
  retrieved_chunk_ids: number[];
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
