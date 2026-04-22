import json
import secrets
from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from embedder import Embedder

class Database:
    def __init__(self, config: dict, minconn: int = 2, maxconn: int = 10):
        self._pool = ThreadedConnectionPool(
            minconn, maxconn,
            dbname=config['db_name'],
            user=config['db_user'],
            password=config['db_password'],
            host="localhost",
            port=5432,
        )
        self.ph = PasswordHasher(
            time_cost=2,
            memory_cost=65536,
            parallelism=2,
        )
        self.embedder = Embedder()


    @contextmanager
    def _conn(self):
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def _sync_chunks(self, cur, text_id: int, content: str):
        chunks = self.embedder.chunk_text(content)
        vectors = self.embedder.embed(chunks)

        cur.execute("DELETE FROM text_chunks WHERE text_id = %s", (text_id,))

        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            cur.execute("""
                INSERT INTO text_chunks (text_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s)
            """, (text_id, i, chunk, vector))

    def retrieve(self, domain_token: str, question: str, top_k: int = 5):
        q_vector = self.embedder.embed([question])[0]
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT text_chunks.chunk_text
                        FROM text_chunks
                        JOIN texts ON texts.id = text_chunks.text_id
                        JOIN data ON data.id = texts.data_id
                        WHERE data.token = %s
                        AND text_chunks.embedding <=> %s::vector < 0.4
                        ORDER BY text_chunks.embedding <=> %s::vector
                        LIMIT %s
                    """, (domain_token, q_vector,q_vector, top_k))
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(e)
            return []

    def create_tables(self):
        with open("resources/schema.sql") as f:
            query = f.read()
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
        except Exception as e:
            print(e)

    def create_user(self, username: str, password: str):
        hashed = self.ph.hash(password)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;",
                        (username, hashed),
                    )
                    return cur.fetchone()[0]
        except Exception as e:
            print(e)
            return None

    def add_website(self, domain: str, user_id: int):
        token = secrets.token_urlsafe(32)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO data (user_id, domain, token) VALUES (%s, %s, %s);",
                        (user_id, domain, token),
                    )
        except Exception as e:
            print(e)
            return None

    def add_source(self, data_token: str, name: str, text: str):
        token = secrets.token_urlsafe(32)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO texts (data_id, name, descr, token) VALUES "
                        "((SELECT id FROM data WHERE token=%s), %s, %s, %s) RETURNING id",
                        (data_token, name, text, token),
                    )
                    text_id = cur.fetchone()[0]
                    self._sync_chunks(cur, text_id, text)
        except Exception as e:
            print(e)
            return None

    def update_source(self, source_token: str, new_text: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE texts SET descr=%s WHERE token=%s RETURNING id",
                        (new_text, source_token),
                    )
                    row = cur.fetchone()
                    if row:
                        self._sync_chunks(cur, row[0], new_text)
        except Exception as e:
            print(e)
            return None

    def get_all_texts(self, domain_token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT name, descr, token FROM texts "
                        "WHERE data_id IN (SELECT id FROM data WHERE token=%s)",
                        (domain_token,),
                    )
                    return cur.fetchall()
        except Exception as e:
            print(e)
            return None

    def get_all_text(self, domain_token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT descr FROM texts "
                        "WHERE data_id IN (SELECT id FROM data WHERE token=%s)",
                        (domain_token,),
                    )
                    rows = cur.fetchall()
                    return "".join(row[0] + "\n" for row in rows)
        except Exception as e:
            print(e)
            return None
        

    def get_data(self, user_id: int):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT domain, token FROM data WHERE user_id=%s",
                        (user_id,),
                    )
                    return [{'domain': row[0], 'token': row[1]} for row in cur.fetchall()]
        except Exception as e:
            print(e)
            return None

    def check_password(self, username: str, password: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, password FROM users WHERE username=%s",
                        (username,),
                    )
                    row = cur.fetchone()
                    if row and self.ph.verify(row[1], password):
                        return row[0]
                    return None
        except VerifyMismatchError:
            return None
        except Exception as e:
            print(e)
            return None

    def update_text(self, token: str, text: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE texts SET descr=%s WHERE token=%s RETURNING id",
                        (text, token),
                    )
                    row = cur.fetchone()
                    if row:
                        self._sync_chunks(cur, row[0], text)
            return True
        except Exception as e:
            print(e)
            return False
        
    def remove_text(self, token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM texts WHERE token=%s",
                        (token,),
                    )
            return True
        except Exception as e:
            print(e)
            return False
        
    def update_fallback(self, token: str, text: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE data SET msg=%s WHERE token=%s",
                        (text, token),
                    )
            return True
        except Exception as e:
            print(e)
            return False

    def check_token(self, user_id: int, token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM data "
                        "WHERE id IN (SELECT data_id FROM texts WHERE token=%s) AND user_id=%s",
                        (token, user_id),
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            print(e)
            return None

    def check_data_token(self, user_id: int, token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM data WHERE user_id=%s AND token=%s",
                        (user_id, token),
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            print(e)
            return None
        
    def remove_website(self, token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM data WHERE token=%s", (token,))
            return True
        except Exception as e:
            print(e)
            return False

    def get_bot_name(self, domain_token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM data WHERE token=%s", (domain_token,))
                    row = cur.fetchone()
                    return row[0] if row else 'Support Bot'
        except Exception as e:
            print(e)
            return 'Support Bot'

    def update_bot_name(self, domain_token: str, name: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE data SET name=%s WHERE token=%s", (name, domain_token))
            return True
        except Exception as e:
            print(e)
            return False

    def get_fallback(self, domain_token):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT msg FROM data WHERE token=%s",
                        (domain_token,),
                    )
                    return cur.fetchone()
        except Exception as e:
            print(e)
            return "Unfortunatelly, I can't answer your question right now."
        
    def get_users(self):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, credits FROM users ORDER BY username"
                    )
                    return [{'id': r[0], 'username': r[1], 'credits': r[2]} for r in cur.fetchall()]
        except Exception as e:
            print(e)
            return []

    def set_credits(self, user_id: int, credits: int):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET credits=%s WHERE id=%s AND user_role='user'",
                        (credits, user_id),
                    )
            return True
        except Exception as e:
            print(e)
            return False

    def get_credits(self, domain_token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT credits FROM users WHERE id = (SELECT user_id FROM data WHERE token=%s)",
                        (domain_token,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            print(e)
            return 0

    def deduct_credit(self, domain_token: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET credits = credits - 1 "
                        "WHERE id = (SELECT user_id FROM data WHERE token=%s) AND credits > 0",
                        (domain_token,),
                    )
            return True
        except Exception as e:
            print(e)
            return False

    def get_credits_by_user(self, user_id: int):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT credits FROM users WHERE id=%s", (user_id,))
                    row = cur.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            print(e)
            return 0

    def change_password(self, user_id: int, old_password: str, new_password: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT password FROM users WHERE id=%s", (user_id,))
                    row = cur.fetchone()
                    if not row or not self.ph.verify(row[0], old_password):
                        return False
                    cur.execute(
                        "UPDATE users SET password=%s WHERE id=%s",
                        (self.ph.hash(new_password), user_id),
                    )
            return True
        except VerifyMismatchError:
            return False
        except Exception as e:
            print(e)
            return False

    def get_role(self, user_id: int):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_role FROM users WHERE id=%s", (user_id,))
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            print(e)
            return None

    def user_exists(self, username):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM users WHERE username=%s",
                        (username,),
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            print(e)
            return None
        
        
