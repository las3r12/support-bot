CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    user_role TEXT CHECK (user_role IN ('admin', 'user')) DEFAULT 'user',
    credits INTEGER NOT NULL DEFAULT 1000,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain VARCHAR(200) NOT NULL,
    UNIQUE (user_id, domain),
    name VARCHAR(200) NOT NULL DEFAULT 'Support Bot',
    hello_msg TEXT DEFAULT 'Hello! How can I help you today?',
    msg TEXT DEFAULT 'Unfortunately I can not answer your question.',
    token CHAR(43) NOT NULL UNIQUE,
    bot_enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS texts (
    id SERIAL PRIMARY KEY,
    data_id INTEGER NOT NULL REFERENCES data(id) ON DELETE CASCADE,
    name VARCHAR(200),
    UNIQUE (data_id, name),
    descr TEXT,
    token CHAR(43) NOT NULL UNIQUE
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
    ON text_chunks USING hnsw (embedding vector_cosine_ops);

