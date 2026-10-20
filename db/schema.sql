CREATE TABLE IF NOT EXISTS etch_cases (
    id text PRIMARY KEY,
    data jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS etch_documents (
    id text PRIMARY KEY,
    data jsonb NOT NULL
);
