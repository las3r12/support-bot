import json
import hashlib
import time
import traceback
from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError



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
        token = hashlib.sha256((str(time.time()) + str(user_id)).encode()).hexdigest()[:32]
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
        token = hashlib.sha256((str(time.time()) + text).encode()).hexdigest()[:32]
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO texts (data_id, name, descr, token) VALUES "
                        "((SELECT id FROM data WHERE token=%s), %s, %s, %s)",
                        (data_token, name, text, token),
                    )
        except Exception as e:
            print(e)
            return None

    def update_source(self, source_token: str, new_text: str):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE texts SET descr=%s WHERE token=%s",
                        (new_text, source_token),
                    )
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
                        "UPDATE texts SET descr=%s WHERE token=%s",
                        (text, token),
                    )
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
        
        
