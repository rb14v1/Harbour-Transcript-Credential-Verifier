"""
Idempotent seed data migration: demo users, applicants, credentials (already
processed, with records + chunks populated), the chunks pushed into the
(stub, in-memory) search index, and a few sample equivalency-query history
rows. Safe to run more than once (get_or_create everywhere), and never calls
set_password() on a historical model - passwords are hashed up front with
django.contrib.auth.hashers.make_password().
"""
from django.db import migrations
from django.contrib.auth.hashers import make_password

from apps.common import ai, search_store

SEARCH_INDEX_NAME = "credential_chunks"

DEMO_PASSWORD = "DemoPass123!"

COURSE_GRADES = ["A", "A-", "B+", "B", "B-", "C+"]
COURSE_TERMS = ["Fall 2019", "Spring 2020", "Fall 2020", "Spring 2021", "Fall 2021", "Spring 2022", "Fall 2022", "Spring 2023"]


def _grade(i):
    return COURSE_GRADES[i % len(COURSE_GRADES)]


def _term(i):
    return COURSE_TERMS[i % len(COURSE_TERMS)]


APPLICANTS = [
    {"full_name": "Jordan Lee", "email": "jordan.lee@example.com"},
    {"full_name": "Casey Kim", "email": "casey.kim@example.com"},
    {"full_name": "Taylor Brooks", "email": "taylor.brooks@example.com"},
    {"full_name": "Sam Patel", "email": "sam.patel@example.com"},
    {"full_name": "Alex Nguyen", "email": "alex.nguyen@example.com"},
]

# applicant email -> list of credentials, each with its course rows
CREDENTIALS = {
    "jordan.lee@example.com": [
        {
            "institution": "State University",
            "credential_type": "transcript",
            "issue_date": "2022-05-15",
            "courses": ["Data Structures and Algorithms", "Computer Architecture", "Discrete Mathematics", "Operating Systems"],
        },
        {
            "institution": "Online Academy",
            "credential_type": "certificate",
            "issue_date": "2023-01-10",
            "courses": ["Intro to Machine Learning", "Applied Statistics"],
        },
    ],
    "casey.kim@example.com": [
        {
            "institution": "Pacific College",
            "credential_type": "transcript",
            "issue_date": "2021-06-01",
            "courses": ["Introduction to Programming", "Linear Algebra", "Database Systems", "Software Engineering Principles"],
        },
        {
            "institution": "Pacific College",
            "credential_type": "diploma",
            "issue_date": "2021-06-15",
            "courses": ["Capstone Project", "Technical Communication"],
        },
    ],
    "taylor.brooks@example.com": [
        {
            "institution": "Riverside Institute of Technology",
            "credential_type": "transcript",
            "issue_date": "2020-12-20",
            "courses": ["Algorithms and Complexity", "Computer Networks", "Discrete Structures", "Web Application Development"],
        },
    ],
    "sam.patel@example.com": [
        {
            "institution": "Northbridge University",
            "credential_type": "transcript",
            "issue_date": "2023-05-30",
            "courses": ["Object Oriented Programming", "Data Structures", "Theory of Computation", "Distributed Systems"],
        },
        {
            "institution": "CloudSkills Academy",
            "credential_type": "certificate",
            "issue_date": "2024-02-14",
            "courses": ["Cloud Computing Fundamentals", "DevOps Practices"],
        },
    ],
    "alex.nguyen@example.com": [
        {
            "institution": "Lakeside College",
            "credential_type": "transcript",
            "issue_date": "2019-05-20",
            "courses": ["Intro to Computer Science", "Calculus II", "Data Structures and Algorithms", "Artificial Intelligence Foundations"],
        },
        {
            "institution": "Lakeside College",
            "credential_type": "diploma",
            "issue_date": "2019-05-25",
            "courses": ["Senior Design Project"],
        },
    ],
}

SAMPLE_QUESTIONS = [
    # (applicant_email, credential_index_within_applicant, question_text)
    ("jordan.lee@example.com", 0, "Does this transcript cover material equivalent to our CS301 (Data Structures) course?"),
    ("sam.patel@example.com", 0, "Would this applicant's coursework satisfy a Theory of Computation prerequisite?"),
    ("alex.nguyen@example.com", 0, "Is there coverage of introductory AI concepts comparable to our AI201 course?"),
]


def seed_demo_data(apps, schema_editor):
    User = apps.get_model("users", "User")
    Applicant = apps.get_model("applicants", "Applicant")
    Credential = apps.get_model("credentials", "Credential")
    CredentialRecord = apps.get_model("credentials", "CredentialRecord")
    CredentialChunk = apps.get_model("credentials", "CredentialChunk")
    EquivalencyQuery = apps.get_model("equivalency", "EquivalencyQuery")

    # --- Users ---------------------------------------------------------------
    admin_user, _ = User.objects.get_or_create(
        email="admin@example.com",
        defaults={
            "full_name": "Avery Admin",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
            "password": make_password(DEMO_PASSWORD),
        },
    )
    reviewer_user, _ = User.objects.get_or_create(
        email="reviewer@example.com",
        defaults={
            "full_name": "Riley Reviewer",
            "role": "admissions_reviewer",
            "password": make_password(DEMO_PASSWORD),
        },
    )
    reviewer2_user, _ = User.objects.get_or_create(
        email="reviewer2@example.com",
        defaults={
            "full_name": "Morgan Reviewer",
            "role": "admissions_reviewer",
            "password": make_password(DEMO_PASSWORD),
        },
    )

    # --- Applicants ------------------------------------------------------------
    applicants_by_email = {}
    for row in APPLICANTS:
        applicant, _ = Applicant.objects.get_or_create(
            email=row["email"],
            defaults={"full_name": row["full_name"]},
        )
        applicants_by_email[row["email"]] = applicant

    # --- Credentials + records + chunks (pre-processed) -------------------------
    search_items = []
    credentials_by_email = {}
    for email, cred_rows in CREDENTIALS.items():
        applicant = applicants_by_email[email]
        credentials_by_email.setdefault(email, [])
        for cred_row in cred_rows:
            credential, created = Credential.objects.get_or_create(
                applicant=applicant,
                institution=cred_row["institution"],
                credential_type=cred_row["credential_type"],
                defaults={
                    "issue_date": cred_row["issue_date"],
                    "blob_path": f"stub://credentials/seed_{applicant.id}_{cred_row['institution'].replace(' ', '_')}.txt",
                    "status": "processed",
                    "uploaded_by": reviewer_user,
                },
            )
            credentials_by_email[email].append(credential)

            if not created:
                # Already seeded on a previous run - leave records/chunks as-is.
                continue

            for idx, course in enumerate(cred_row["courses"]):
                record = CredentialRecord.objects.create(
                    credential=credential,
                    course_or_subject=course,
                    grade_or_score=_grade(idx),
                    term=_term(idx),
                )
                chunk_text = (
                    f"{applicant.full_name} studied {record.course_or_subject} "
                    f"at {credential.institution} during {record.term}, "
                    f"achieving a grade/score of {record.grade_or_score}."
                )
                search_doc_id = f"credential-{credential.id}-chunk-{idx}"
                chunk = CredentialChunk.objects.create(
                    credential=credential,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    search_doc_id=search_doc_id,
                )
                vector = ai.generate_embedding(chunk_text)
                search_items.append({
                    "id": search_doc_id,
                    "vector": vector,
                    "payload": {
                        "credential_id": credential.id,
                        "chunk_id": chunk.id,
                        "chunk_text": chunk_text,
                        "course_or_subject": course,
                        "institution": credential.institution,
                    },
                })

    if search_items:
        search_store.upsert_chunks(SEARCH_INDEX_NAME, search_items)

    # --- Sample equivalency-query history ----------------------------------------
    for email, cred_index, question_text in SAMPLE_QUESTIONS:
        credential = credentials_by_email[email][cred_index]
        if EquivalencyQuery.objects.filter(credential=credential, question_text=question_text).exists():
            continue

        query_vector = ai.generate_embedding(question_text)
        results = search_store.search(SEARCH_INDEX_NAME, query_vector, top_k=5)
        scoped = [r for r in results if r["payload"].get("credential_id") == credential.id] or results
        context_lines = "\n".join(f"- {r['payload'].get('chunk_text', '')}" for r in scoped)
        system_prompt = (
            "You are an admissions assistant helping a reviewer assess transfer-credit / "
            "credential equivalency. Use only the provided coursework excerpts, and cite "
            "the specific coursework you relied on."
        )
        user_prompt = (
            f"Question: {question_text}\n\nRetrieved coursework excerpts:\n{context_lines}\n\n"
            "Provide a short, plain-language equivalency recommendation."
        )
        answer_text = ai.chat_completion(system_prompt, user_prompt)
        retrieved_chunk_ids = [r["payload"].get("chunk_id") for r in scoped if r["payload"].get("chunk_id") is not None]

        EquivalencyQuery.objects.create(
            reviewer=reviewer_user,
            credential=credential,
            question_text=question_text,
            answer_text=answer_text,
            retrieved_chunk_ids=retrieved_chunk_ids,
        )


def unseed_demo_data(apps, schema_editor):
    """Best-effort reverse: removes exactly the rows this migration creates."""
    User = apps.get_model("users", "User")
    Applicant = apps.get_model("applicants", "Applicant")

    User.objects.filter(email__in=[
        "admin@example.com", "reviewer@example.com", "reviewer2@example.com",
    ]).delete()
    Applicant.objects.filter(email__in=[row["email"] for row in APPLICANTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
        ("applicants", "0001_initial"),
        ("credentials", "0002_initial"),
        ("equivalency", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, unseed_demo_data),
    ]
