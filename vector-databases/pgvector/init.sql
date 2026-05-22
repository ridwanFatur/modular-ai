CREATE EXTENSION IF NOT EXISTS vector;
SELECT * FROM pg_extension;

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(768)
);