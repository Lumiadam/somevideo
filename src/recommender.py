import sqlite3
from src.data_manager import get_db_connection

def get_recommendations(username, group_id=None, limit=5):
    """
    Generate recommendations for a user:
    1. If guest or no username: return top-rated Public + Active movies inside this group.
    2. Otherwise, find the user's favorite genre based on behavior in the current group.
    3. Recommend highest rated movies of that genre that the user has permission to see, hasn't rated yet in that group, and belong to that group.
    4. Fallback to top rated movies they have permission to see, hasn't rated yet, and belong to that group.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Standardize group_id
    if group_id == 0 or group_id == "None":
        group_id = None
        
    recommended_movies = []
    
    if not username or username == 'guest':
        # Guest mode: only recommend Public + Active movies inside this group
        if group_id is not None:
            cursor.execute("""
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
                JOIN Group_Movies gm ON m.id = gm.movie_id AND gm.status = 'Active'
                WHERE m.visibility = 'Public' AND m.status = 'Active' AND gm.group_id = ?
                GROUP BY m.id
                ORDER BY avg_rating DESC, m.release_year DESC
                LIMIT ?
            """, (group_id, limit))
        else:
            cursor.execute("""
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
                WHERE m.visibility = 'Public' AND m.status = 'Active'
                GROUP BY m.id
                ORDER BY avg_rating DESC, m.release_year DESC
                LIMIT ?
            """, (limit,))
        recommended_movies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return recommended_movies
        
    # 1. Find the user's favorite genre in this group (considering visibility rules)
    cursor.execute("""
        SELECT m.genre, COUNT(*) as interaction_count
        FROM User_Behavior ub
        JOIN Movie m ON ub.movie_id = m.id
        WHERE ub.username = ? 
          AND (ub.group_id = ? OR (ub.group_id IS NULL AND ? IS NULL))
          AND ub.behavior_type IN ('view', 'rate', 'like')
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
        GROUP BY m.genre
        ORDER BY interaction_count DESC
        LIMIT 1
    """, (username, group_id, group_id, username, username))
    
    favorite_genre_row = cursor.fetchone()
    
    if favorite_genre_row:
        favorite_genre = favorite_genre_row["genre"]
        
        # 2. Find movies of this favorite genre that the user hasn't rated yet IN THIS GROUP (under visibility and group constraints)
        if group_id is not None:
            cursor.execute("""
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
                JOIN Group_Movies gm ON m.id = gm.movie_id AND gm.status = 'Active'
                WHERE m.genre = ? AND gm.group_id = ?
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
                  AND m.id NOT IN (
                      SELECT movie_id FROM User_Behavior 
                      WHERE username = ? 
                        AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
                        AND behavior_type = 'rate'
                  )
                GROUP BY m.id
                ORDER BY avg_rating DESC, m.release_year DESC
                LIMIT ?
            """, (favorite_genre, group_id, username, username, username, group_id, group_id, limit))
        else:
            cursor.execute("""
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
                WHERE m.genre = ?
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
                  AND m.id NOT IN (
                      SELECT movie_id FROM User_Behavior 
                      WHERE username = ? 
                        AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
                        AND behavior_type = 'rate'
                  )
                GROUP BY m.id
                ORDER BY avg_rating DESC, m.release_year DESC
                LIMIT ?
            """, (favorite_genre, username, username, username, group_id, group_id, limit))
            
        recommended_movies = [dict(row) for row in cursor.fetchall()]
        
    # 3. Cold start or not enough recommendations: pad with top rated movies overall (under visibility and group constraints)
    needed = limit - len(recommended_movies)
    if needed > 0:
        excluded_ids = [m["id"] for m in recommended_movies]
        
        if group_id is not None:
            query = """
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
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
                  AND m.id NOT IN (
                      SELECT movie_id FROM User_Behavior 
                      WHERE username = ? 
                        AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
                        AND behavior_type = 'rate'
                  )
            """
            params = [group_id, username, username, username, group_id, group_id]
        else:
            query = """
                SELECT m.id, m.title, m.genre, m.description, m.release_year, m.duration, m.poster_path,
                       COALESCE(AVG(CASE WHEN ub_all.behavior_type = 'rate' THEN ub_all.rating END), 0.0) as avg_rating,
                       COUNT(CASE WHEN ub_all.behavior_type = 'view' THEN 1 END) as view_count
                FROM Movie m
                LEFT JOIN User_Behavior ub_all ON m.id = ub_all.movie_id
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
                  AND m.id NOT IN (
                      SELECT movie_id FROM User_Behavior 
                      WHERE username = ? 
                        AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
                        AND behavior_type = 'rate'
                  )
            """
            params = [username, username, username, group_id, group_id]
            
        if excluded_ids:
            placeholders = ",".join("?" for _ in excluded_ids)
            query += f" AND m.id NOT IN ({placeholders})"
            params.extend(excluded_ids)
            
        query += """
            GROUP BY m.id
            ORDER BY avg_rating DESC, m.release_year DESC
            LIMIT ?
        """
        params.append(needed)
        
        cursor.execute(query, params)
        fallback_movies = [dict(row) for row in cursor.fetchall()]
        recommended_movies.extend(fallback_movies)
        
    conn.close()
    return recommended_movies
