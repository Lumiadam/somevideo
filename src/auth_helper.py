import sqlite3
from src.data_manager import get_db_connection
from src.init_db import hash_password

def get_auth_config():
    """
    Query all users from SQLite and format them into credentials for streamlit-authenticator.
    Returns the config dictionary and a mapping of username -> role.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, email, name, role FROM User")
    rows = cursor.fetchall()
    conn.close()
    
    usernames = {}
    roles = {}
    for row in rows:
        usernames[row["username"]] = {
            "email": row["email"],
            "name": row["name"],
            "password": row["password"]
        }
        roles[row["username"]] = row["role"]
        
    config = {
        "credentials": {
            "usernames": usernames
        },
        "cookie": {
            "expiry_days": 1,
            "key": "movie_recommender_auth_cookie_key",
            "name": "movie_recommender_auth_cookie"
        }
    }
    return config, roles

def register_user(username, password, email, name, role='user'):
    """
    Register a new user in the database, hashing their password.
    """
    if not username or not password or not email or not name:
        return False, "所有欄位皆為必填！"
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO User (username, password, email, name, role) VALUES (?, ?, ?, ?, ?)",
            (username, hashed, email, name, role)
        )
        conn.commit()
        success = True
        error_msg = ""
    except sqlite3.IntegrityError:
        success = False
        error_msg = "帳號已被佔用，請更換帳號。"
    except Exception as e:
        success = False
        error_msg = str(e)
    finally:
        conn.close()
        
    return success, error_msg
