CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain TEXT UNIQUE,
    msg TEXT,
    token TEXT
);

CREATE TABLE IF NOT EXISTS texts (
    id SERIAL PRIMARY KEY,
    data_id INTEGER NOT NULL REFERENCES data(id) ON DELETE CASCADE,
    name TEXT UNIQUE,
    descr TEXT,
    token TEXT
);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS text_chunks (
    id          SERIAL PRIMARY KEY,
    text_id     INTEGER NOT NULL REFERENCES texts(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text  TEXT NOT NULL,
    embedding   vector(384),
    UNIQUE (text_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS text_chunks_embedding_idx
    ON text_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
