import psycopg2
import traceback
import json

def get_conn():
    with open("resources/config.json", 'r') as f:
        config = json.load(f)
        conn = psycopg2.connect(
                dbname=config['db_name'],
                user=config['db_user'],
                password=config['db_password'],
                host="localhost",
                port=5432
            )
    return conn

def create_tables():
    with open("resources/schema.sql") as f:
        query = f.read()
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query)

    except Exception as e:
        traceback.print_exc()
        return None
        
def create_user(username: str, password: str, domain: str, text: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;",
                    (username, password)
                )
                user_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO data (user_id, domain, descr) VALUES (%s, %s, %s);",
                    (user_id, domain, text)
                )

            return user_id

    except Exception as e:
        traceback.print_exc()
        return None

def get_text(user_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select descr from data where user_id=%s", 
                    (user_id,)
                )
                text = cur.fetchone()[0]
                print(text)
                return text
    except Exception as e:
        print('Error: ', e)
        return None
        
def check_password(username, password):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select id from users where username=%s and password=%s",
                    (username, password)
                )
                id = cur.fetchone()
                return id[0] if id else None
    except Exception as e:
        print('Error: ', e)
        return None
