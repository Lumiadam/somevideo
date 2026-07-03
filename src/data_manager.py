import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "recommender.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_movie(movie_id, username=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if not username or username == 'guest':
        cursor.execute("""
            SELECT m.*,
                   COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                   COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
            FROM Movie m 
            LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
            WHERE m.id = ? AND m.visibility = 'Public' AND m.status = 'Active'
            GROUP BY m.id
        """, (movie_id,))
    else:
        cursor.execute("""
            SELECT m.*,
                   COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                   COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
            FROM Movie m
            LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
            WHERE m.id = ? 
              AND (
                  (m.visibility = 'Public' AND m.status = 'Active')
                  OR (m.uploaded_by = ?)
                  OR (m.visibility = 'Semi-Public' AND m.status = 'Active' AND m.uploaded_by IN (
                      SELECT gm2.username 
                      FROM Group_Members gm1
                      JOIN Group_Members gm2 ON gm1.group_id = gm2.group_id
                      WHERE gm1.username = ? AND gm1.status = 'Joined' AND gm2.status = 'Joined'
                  ))
              )
            GROUP BY m.id
        """, (movie_id, username, username))
        
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_movies(username=None, search_query="", genre_filter="全部", show_mine_only=False, group_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if group_id == 0 or group_id == "None":
        group_id = None
        
    if show_mine_only and username and username != 'guest':
        if group_id is not None:
            query = """
                SELECT m.*, 
                       COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                       COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                JOIN Group_Movies gm ON m.id = gm.movie_id AND gm.status = 'Active'
                WHERE m.uploaded_by = ? AND gm.group_id = ?
            """
            params = [username, group_id]
        else:
            query = """
                SELECT m.*, 
                       COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                       COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                WHERE m.uploaded_by = ?
            """
            params = [username]
    else:
        if not username or username == 'guest':
            if group_id is not None:
                query = """
                    SELECT m.*, 
                           COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                           COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                           COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                    FROM Movie m
                    LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                    JOIN Group_Movies gm ON m.id = gm.movie_id AND gm.status = 'Active'
                    WHERE m.visibility = 'Public' AND m.status = 'Active' AND gm.group_id = ?
                """
                params = [group_id]
            else:
                query = """
                    SELECT m.*, 
                           COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                           COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                           COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                    FROM Movie m
                    LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                    WHERE m.visibility = 'Public' AND m.status = 'Active'
                """
                params = []
        else:
            if group_id is not None:
                query = """
                    SELECT m.*, 
                           COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                           COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                           COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                    FROM Movie m
                    LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                    JOIN Group_Movies gm ON m.id = gm.movie_id AND gm.status = 'Active'
                    WHERE gm.group_id = ?
                      AND (
                          (m.visibility = 'Public' AND m.status = 'Active')
                          OR (m.uploaded_by = ?)
                          OR (m.visibility = 'Semi-Public' AND m.status = 'Active' AND m.uploaded_by IN (
                              SELECT gm2.username 
                              FROM Group_Members gm1
                              JOIN Group_Members gm2 ON gm1.group_id = gm2.group_id
                              WHERE gm1.username = ? AND gm1.status = 'Joined' AND gm2.status = 'Joined'
                          ))
                      )
                """
                params = [group_id, username, username]
            else:
                query = """
                    SELECT m.*, 
                           COALESCE(AVG(CASE WHEN ub.behavior_type = 'rate' THEN ub.rating END), 0.0) as avg_rating,
                           COUNT(CASE WHEN ub.behavior_type = 'rate' THEN 1 END) as rating_count,
                           COUNT(CASE WHEN ub.behavior_type = 'view' THEN 1 END) as view_count
                    FROM Movie m
                    LEFT JOIN User_Behavior ub ON m.id = ub.movie_id
                    WHERE (
                        (m.visibility = 'Public' AND m.status = 'Active')
                        OR (m.uploaded_by = ?)
                        OR (m.visibility = 'Semi-Public' AND m.status = 'Active' AND m.uploaded_by IN (
                            SELECT gm2.username 
                            FROM Group_Members gm1
                            JOIN Group_Members gm2 ON gm1.group_id = gm2.group_id
                            WHERE gm1.username = ? AND gm1.status = 'Joined' AND gm2.status = 'Joined'
                        ))
                    )
                """
                params = [username, username]
                
    if search_query:
        query += " AND (m.title LIKE ? OR m.description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if genre_filter != "全部":
        query += " AND m.genre = ?"
        params.append(genre_filter)
        
    query += " GROUP BY m.id"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_genres(username=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if not username or username == 'guest':
        cursor.execute("SELECT DISTINCT genre FROM Movie WHERE visibility = 'Public' AND status = 'Active'")
    else:
        cursor.execute("""
            SELECT DISTINCT m.genre FROM Movie m
            WHERE (
                (m.visibility = 'Public' AND m.status = 'Active')
                OR (m.uploaded_by = ?)
                OR (m.visibility = 'Semi-Public' AND m.status = 'Active' AND m.uploaded_by IN (
                    SELECT gm2.username 
                    FROM Group_Members gm1
                    JOIN Group_Members gm2 ON gm1.group_id = gm2.group_id
                    WHERE gm1.username = ? AND gm1.status = 'Joined' AND gm2.status = 'Joined'
                ))
            )
        """, (username, username))
    rows = cursor.fetchall()
    conn.close()
    return [row["genre"] for row in rows]

def log_behavior(username, movie_id, behavior_type, rating=None, group_id=None):
    """
    Log user behavior (view, rate, like, rec_show, rec_click).
    Handles rate updates: if user has already rated a movie, update the rating.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Standardize group_id
    if group_id == 0 or group_id == "None":
        group_id = None
        
    if behavior_type == 'rate':
        # Check if already rated in this group context
        cursor.execute("""
            SELECT id FROM User_Behavior 
            WHERE username = ? AND movie_id = ? AND behavior_type = 'rate'
              AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
        """, (username, movie_id, group_id, group_id))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE User_Behavior 
                SET rating = ?, timestamp = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, existing["id"]))
        else:
            cursor.execute("""
                INSERT INTO User_Behavior (username, movie_id, behavior_type, rating, group_id)
                VALUES (?, ?, 'rate', ?, ?)
            """, (username, movie_id, rating, group_id))
    elif behavior_type == 'like':
        # Toggle like or check if already liked in this group context
        cursor.execute("""
            SELECT id FROM User_Behavior 
            WHERE username = ? AND movie_id = ? AND behavior_type = 'like'
              AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
        """, (username, movie_id, group_id, group_id))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO User_Behavior (username, movie_id, behavior_type, group_id)
                VALUES (?, ?, 'like', ?)
            """, (username, movie_id, group_id))
    else:
        # Standard insert for view, rec_show, rec_click
        cursor.execute("""
            INSERT INTO User_Behavior (username, movie_id, behavior_type, group_id)
            VALUES (?, ?, ?, ?)
        """, (username, movie_id, behavior_type, group_id))
        
    conn.commit()
    conn.close()

def log_recommendation_impressions(username, movie_ids, group_id=None):
    """
    Logs multiple recommendation impressions in a single transaction.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    if group_id == 0 or group_id == "None":
        group_id = None
    for mid in movie_ids:
        cursor.execute("""
            INSERT INTO User_Behavior (username, movie_id, behavior_type, group_id)
            VALUES (?, ?, 'rec_show', ?)
        """, (username, mid, group_id))
    conn.commit()
    conn.close()

def add_movie(title, genre, description, release_year, duration, poster_path="src/assets/default.png", video_path=None, status="Pending", uploaded_by="system", visibility="Public", cover_url=None, video_preview_url=None, group_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Movie (title, genre, description, release_year, duration, poster_path, video_path, status, uploaded_by, visibility, cover_url, video_preview_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, genre, description, release_year, duration, poster_path, video_path, status, uploaded_by, visibility, cover_url, video_preview_url))
    movie_id = cursor.lastrowid
    
    if group_id == 0 or group_id == "None":
        group_id = None
        
    if group_id is not None:
        # Determine status: default to Active for system seeding or group owner, else Pending
        cursor.execute("SELECT created_by FROM Groups WHERE group_id = ?", (group_id,))
        group_row = cursor.fetchone()
        owner = group_row["created_by"] if group_row else None
        
        status_in_group = "Active"
        if uploaded_by != "system" and uploaded_by != "admin" and uploaded_by != owner:
            if visibility in ("Public", "Semi-Public"):
                status_in_group = "Pending"
                
        cursor.execute("""
            INSERT OR REPLACE INTO Group_Movies (group_id, movie_id, status, shared_by)
            VALUES (?, ?, ?, ?)
        """, (group_id, movie_id, status_in_group, uploaded_by))
        
    conn.commit()
    conn.close()
    return movie_id

# --- Admin audit and group management APIs ---

def get_pending_movies():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Exclude Private movies from Admin Pending view completely
    cursor.execute("SELECT * FROM Movie WHERE status = 'Pending' AND visibility != 'Private' ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_movie_status(movie_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Movie SET status = ? WHERE id = ?", (status, movie_id))
    conn.commit()
    conn.close()

def create_group(name, created_by):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Groups (name, created_by) VALUES (?, ?)", (name, created_by))
        group_id = cursor.lastrowid
        # Creator automatically joins as Owner with status Joined
        cursor.execute("INSERT INTO Group_Members (group_id, username, group_role, status) VALUES (?, ?, 'Owner', 'Joined')", (group_id, created_by))
        conn.commit()
        success = True
        msg = f"群組「{name}」建立成功！您已自動成為群組建立者。"
    except sqlite3.IntegrityError:
        success = False
        msg = "群組名稱已存在，請更換名稱。"
    except Exception as e:
        success = False
        msg = str(e)
    conn.close()
    return success, msg

def join_group(group_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Group_Members (group_id, username, group_role, status) VALUES (?, ?, 'Member', 'Pending_Approval')", (group_id, username))
        conn.commit()
        success = True
        msg = "已送出加入申請，請等待群組建立者審核。"
    except sqlite3.IntegrityError:
        success = False
        msg = "您已申請加入或已是該群組成員。"
    except Exception as e:
        success = False
        msg = str(e)
    conn.close()
    return success, msg

def get_group_pending_members(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT gm.group_id, g.name as group_name, gm.username as applicant
        FROM Group_Members gm
        JOIN Groups g ON gm.group_id = g.group_id
        WHERE gm.status = 'Pending_Approval'
          AND g.group_id IN (
              SELECT group_id FROM Group_Members 
              WHERE username = ? AND group_role = 'Owner' AND status = 'Joined'
          )
        ORDER BY gm.joined_at DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_group_member_status(group_id, member_username, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Group_Members 
        SET status = ? 
        WHERE group_id = ? AND username = ?
    """, (status, group_id, member_username))
    conn.commit()
    conn.close()

def get_user_groups(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.*, gm.group_role, gm.status as member_status FROM Groups g
        JOIN Group_Members gm ON g.group_id = gm.group_id
        WHERE gm.username = ? AND gm.status = 'Joined'
        ORDER BY g.name ASC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_memberships_status(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.name as group_name, gm.group_role, gm.status, gm.group_id
        FROM Group_Members gm
        JOIN Groups g ON gm.group_id = g.group_id
        WHERE gm.username = ?
        ORDER BY g.name ASC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Groups ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_ratings(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ub.id, m.title, m.genre, ub.rating, ub.timestamp
        FROM User_Behavior ub
        JOIN Movie m ON ub.movie_id = m.id
        WHERE ub.username = ? AND ub.behavior_type = 'rate'
        ORDER BY ub.timestamp DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Admin Panel Metrics and Analytics ---

def get_admin_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total users (excluding admin)
    cursor.execute("SELECT COUNT(*) FROM User WHERE role = 'user'")
    total_users = cursor.fetchone()[0]
    
    # 2. Total movies
    cursor.execute("SELECT COUNT(*) FROM Movie")
    total_movies = cursor.fetchone()[0]
    
    # 3. Total ratings
    cursor.execute("SELECT COUNT(*) FROM User_Behavior WHERE behavior_type = 'rate'")
    total_ratings = cursor.fetchone()[0]
    
    # 4. Average rating
    cursor.execute("SELECT AVG(rating) FROM User_Behavior WHERE behavior_type = 'rate'")
    avg_rating = cursor.fetchone()[0]
    avg_rating = round(avg_rating, 2) if avg_rating else 0.0
    
    # 5. Recommendation CTR
    cursor.execute("SELECT COUNT(*) FROM User_Behavior WHERE behavior_type = 'rec_click'")
    rec_clicks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM User_Behavior WHERE behavior_type = 'rec_show'")
    rec_shows = cursor.fetchone()[0]
    
    ctr = round((rec_clicks / rec_shows) * 100, 2) if rec_shows > 0 else 0.0
    
    conn.close()
    return {
        "total_users": total_users,
        "total_movies": total_movies,
        "total_ratings": total_ratings,
        "avg_rating": avg_rating,
        "rec_clicks": rec_clicks,
        "rec_shows": rec_shows,
        "ctr": ctr
    }

def get_rating_distribution():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rating, COUNT(*) as count 
        FROM User_Behavior 
        WHERE behavior_type = 'rate' 
        GROUP BY rating 
        ORDER BY rating
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_genre_distribution():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT genre, COUNT(*) as count 
        FROM Movie 
        GROUP BY genre
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_ctr_over_time():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Group by date or hour depending on granularity. Here we group by date and hour (YYYY-MM-DD HH:00) to show micro-changes
    cursor.execute("""
        SELECT strftime('%Y-%m-%d %H:00', timestamp) as time_slot,
               SUM(CASE WHEN behavior_type = 'rec_click' THEN 1 ELSE 0 END) as clicks,
               SUM(CASE WHEN behavior_type = 'rec_show' THEN 1 ELSE 0 END) as shows
        FROM User_Behavior
        WHERE behavior_type IN ('rec_click', 'rec_show')
        GROUP BY time_slot
        ORDER BY time_slot
    """)
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        clicks = row["clicks"]
        shows = row["shows"]
        ctr = round((clicks / shows) * 100, 2) if shows > 0 else 0.0
        data.append({
            "time_slot": row["time_slot"],
            "clicks": clicks,
            "shows": shows,
            "ctr": ctr
        })
    return data

def get_user_activity_log():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ub.username, m.title, ub.behavior_type, ub.rating, ub.timestamp
        FROM User_Behavior ub
        JOIN Movie m ON ub.movie_id = m.id
        WHERE ub.behavior_type IN ('view', 'rate', 'like')
        ORDER BY ub.timestamp DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_movie_to_group(group_id, movie_id, shared_by, status="Pending"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO Group_Movies (group_id, movie_id, status, shared_by)
        VALUES (?, ?, ?, ?)
    """, (group_id, movie_id, status, shared_by))
    conn.commit()
    conn.close()

def approve_group_movie(group_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Group_Movies SET status = 'Active'
        WHERE group_id = ? AND movie_id = ?
    """, (group_id, movie_id))
    conn.commit()
    conn.close()

def reject_group_movie(group_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM Group_Movies
        WHERE group_id = ? AND movie_id = ?
    """, (group_id, movie_id))
    conn.commit()
    conn.close()

def get_group_pending_movies(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, gm.shared_by FROM Movie m
        JOIN Group_Movies gm ON m.id = gm.movie_id
        WHERE gm.group_id = ? AND gm.status = 'Pending'
        ORDER BY m.id DESC
    """, (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_movie(movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Group_Movies WHERE movie_id = ?", (movie_id,))
    cursor.execute("DELETE FROM User_Behavior WHERE movie_id = ?", (movie_id,))
    cursor.execute("DELETE FROM Movie WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()

def kick_group_member(group_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM Group_Members
        WHERE group_id = ? AND username = ?
    """, (group_id, username))
    conn.commit()
    conn.close()

def get_group_joined_members(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, group_role FROM Group_Members
        WHERE group_id = ? AND status = 'Joined'
        ORDER BY username ASC
    """, (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_group_active_movies(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, gm.shared_by FROM Movie m
        JOIN Group_Movies gm ON m.id = gm.movie_id
        WHERE gm.group_id = ? AND gm.status = 'Active'
        ORDER BY m.id DESC
    """, (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
