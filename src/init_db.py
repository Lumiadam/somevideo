import sqlite3
import os
import sys

# Setup path to include current dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "recommender.db")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def hash_password(password):
    # Try dynamic hashing using streamlit-authenticator or fallback to bcrypt
    try:
        import streamlit_authenticator as stauth
        try:
            return stauth.Hasher.hash(password)
        except Exception:
            return stauth.Hasher([password]).generate()[0]
    except Exception:
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        except Exception:
            # Simple fallback (only for safety, though bcrypt should be installed)
            import hashlib
            return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_database():
    # Ensure directories exist
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing tables to apply schema modifications
    cursor.execute("DROP TABLE IF EXISTS Group_Movies")
    cursor.execute("DROP TABLE IF EXISTS Group_Members")
    cursor.execute("DROP TABLE IF EXISTS Groups")
    cursor.execute("DROP TABLE IF EXISTS User_Behavior")
    cursor.execute("DROP TABLE IF EXISTS Movie")
    cursor.execute("DROP TABLE IF EXISTS User")
    
    # 1. Create User table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS User (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)
    
    # 2. Create Groups table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Groups (
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_by TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES User(username)
    )
    """)
    
    # 3. Create Group_Members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Group_Members (
        group_id INTEGER,
        username TEXT,
        group_role TEXT NOT NULL DEFAULT 'Member', -- 'Owner', 'Member'
        status TEXT NOT NULL DEFAULT 'Pending_Approval', -- 'Joined', 'Pending_Approval', 'Rejected'
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (group_id, username),
        FOREIGN KEY (group_id) REFERENCES Groups(group_id),
        FOREIGN KEY (username) REFERENCES User(username)
    )
    """)
    
    # 4. Create Movie table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Movie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        description TEXT NOT NULL,
        release_year INTEGER NOT NULL,
        duration TEXT NOT NULL,
        poster_path TEXT NOT NULL,
        video_path TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        uploaded_by TEXT DEFAULT 'system',
        visibility TEXT NOT NULL DEFAULT 'Public', -- 'Private', 'Semi-Public', 'Public'
        cover_url TEXT,
        video_preview_url TEXT
    )
    """)
    
    # 4.5 Create Group_Movies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Group_Movies (
        group_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active', -- 'Active', 'Pending'
        shared_by TEXT DEFAULT 'system',
        PRIMARY KEY (group_id, movie_id),
        FOREIGN KEY (group_id) REFERENCES Groups(group_id) ON DELETE CASCADE,
        FOREIGN KEY (movie_id) REFERENCES Movie(id) ON DELETE CASCADE
    )
    """)
    
    # 5. Create User_Behavior table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS User_Behavior (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        movie_id INTEGER NOT NULL,
        behavior_type TEXT NOT NULL, -- 'view', 'rate', 'like', 'rec_show', 'rec_click'
        rating INTEGER, -- 1-5, NULL if not 'rate'
        group_id INTEGER, -- NULL for personal space, or the ID of the group
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES User(username),
        FOREIGN KEY (movie_id) REFERENCES Movie(id),
        FOREIGN KEY (group_id) REFERENCES Groups(group_id)
    )
    """)
    
    # Clean tables to ensure fresh start
    cursor.execute("DELETE FROM User")
    cursor.execute("DELETE FROM Movie")
    cursor.execute("DELETE FROM Groups")
    cursor.execute("DELETE FROM Group_Members")
    cursor.execute("DELETE FROM User_Behavior")
    cursor.execute("DELETE FROM Group_Movies")
    
    # Insert default users
    default_users = [
        ("admin", hash_password("admin123"), "admin@rec.com", "系統管理員", "admin"),
        ("user1", hash_password("user123"), "user1@rec.com", "陳小明", "user"),
        ("user2", hash_password("user234"), "user2@rec.com", "林美玲", "user"),
        ("user3", hash_password("user345"), "user3@rec.com", "林阿土", "user"),
        ("user4", hash_password("user456"), "user4@rec.com", "王大明", "user"),
        ("user5", hash_password("user567"), "user5@rec.com", "張美美", "user")
    ]
    cursor.executemany("INSERT INTO User VALUES (?, ?, ?, ?, ?)", default_users)
    
    # Insert default groups
    default_groups = [
        (1, "電影研究社", "admin"),
        (2, "搞笑短影音同好會", "user1"),
        (3, "驚悚懸疑同好會", "admin"),
        (4, "動漫與奇幻世界", "admin")
    ]
    cursor.executemany("INSERT INTO Groups (group_id, name, created_by) VALUES (?, ?, ?)", default_groups)
    
    # Insert default group memberships
    default_members = [
        # Group Owners (auto-joined as Owner)
        (1, "admin", "Owner", "Joined"),
        (2, "user1", "Owner", "Joined"),
        (3, "admin", "Owner", "Joined"),
        (4, "admin", "Owner", "Joined"),
        
        # Group Members (Joined)
        (1, "user1", "Member", "Joined"),
        (3, "user1", "Member", "Joined"),
        (1, "user2", "Member", "Joined"),
        (4, "user2", "Member", "Joined"),
        (2, "user3", "Member", "Joined"),
        (3, "user3", "Member", "Joined"),
        (1, "user4", "Member", "Joined"),
        (3, "user4", "Member", "Joined"),
        (4, "user4", "Member", "Joined"),
        (2, "user5", "Member", "Joined"),
        (4, "user5", "Member", "Joined"),
        
        # Pending Approval Member
        (1, "user3", "Member", "Pending_Approval")
    ]
    cursor.executemany("INSERT INTO Group_Members (group_id, username, group_role, status) VALUES (?, ?, ?, ?)", default_members)
    
    # Insert mock movies (id, title, genre, description, release_year, duration, poster_path, video_path, status, uploaded_by, visibility, cover_url, video_preview_url)
    mock_movies = [
        (1, "星際啟示錄", "科幻", "探索未知宇宙深處的史詩冒險，一名太空飛行員必須穿過蟲洞以尋找人類的新家園。", 2014, "169 mins", "src/assets/interstellar.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (2, "霓虹殺手 2099", "動作", "在霓虹閃爍的賽博朋克都市中，一名生化殺手追尋自己失去記憶與陰謀真相。", 2025, "125 mins", "src/assets/cyberpunk.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (3, "夏日落日雙人舞", "浪漫", "在蔚藍海岸的日落時分，兩位不同背景的舞蹈家邂逅，譜出一段酸甜交織的愛情舞曲。", 2023, "110 mins", "src/assets/romance.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (4, "超爆笑辦公室", "喜劇", "充滿各種奇葩員工與荒謬日常的科技公司辦公室，天天上演笑料百出的職場風波。", 2022, "98 mins", "src/assets/comedy.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (5, "霧中迷案", "懸疑", "大霧籠罩的偏遠山莊發生連環失蹤案，一名退休神探在重重迷霧中撥雲見日搜集線留線索。", 2024, "118 mins", "src/assets/thriller.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (6, "神龍傳奇：失落的城堡", "奇幻", "年輕的魔法學徒意外喚醒沉睡千年的守護神龍，踏上尋找失落城堡的奇幻冒險。", 2025, "132 mins", "src/assets/fantasy.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        
        # New Active movies (Public)
        (7, "全面啟動", "科幻", "在夢境深處竊取機密的特工面臨最後一項不可能的任務：植入思想並完成全面啟動。", 2010, "148 mins", "src/assets/interstellar.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (8, "鬼滅之刃：無限列車篇", "奇幻", "炭治郎、禰豆子與炎柱煉獄杏壽郎在火車上面對吞噬乘客的強大夢境惡鬼。", 2020, "117 mins", "src/assets/fantasy.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (9, "隔離島", "懸疑", "兩名聯邦法警調查一家精神病院中瘋狂病人的神秘失蹤，卻陷入重重驚悚迷局。", 2010, "138 mins", "src/assets/thriller.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (10, "醉後大丈夫", "喜劇", "三個死黨在單身派對斷片狂歡後，必須在混亂的拉斯維加斯尋找失蹤的新郎。", 2009, "100 mins", "src/assets/comedy.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (11, "捍衛戰士：獨行俠", "動作", "頂尖飛行員獨行俠重回基地，訓練新一代學員執行極限飛行的危險轟炸任務。", 2022, "130 mins", "src/assets/cyberpunk.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (12, "鐵達尼號", "浪漫", "在悲劇性的鐵達尼號首航中，富家女露絲與窮畫家傑克譜出跨越階級的淒美愛情。", 1997, "194 mins", "src/assets/romance.png", None, "Active", "system", "Public", "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        
        # Pending movies
        (13, "天能", "科幻", "主角必須利用逆轉時間的物理現象阻止世界末日，展開一場跨越時空的情報戰。", 2020, "150 mins", "src/assets/interstellar.png", None, "Pending", "user3", "Public", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        (14, "玩命關頭 X", "動作", "唐老大與他的飛車家人面對來自過去反派的誓死復仇與瘋狂街頭對決。", 2023, "141 mins", "src/assets/cyberpunk.png", None, "Pending", "user4", "Semi-Public", "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (15, "咒", "懸疑", "一位母親為了保護被惡魔詛咒的女兒，不惜用影片記錄並揭開塵封多年的恐怖禁忌。", 2022, "110 mins", "src/assets/thriller.png", None, "Pending", "user5", "Public", "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4"),
        
        # Private and Semi-Public Active movies (uploaded by user1)
        (16, "私密影片示例", "科幻", "這是一部私密影片，只有上傳者 user1 本人可以看到。", 2026, "10 mins", "src/assets/interstellar.png", None, "Active", "user1", "Private", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/movie.mp4"),
        (17, "半公開影片示例", "動作", "這是一部半公開影片，只有上傳者 user1 本人以及與其同處於 Joined 群組的成員可以看到。", 2026, "15 mins", "src/assets/cyberpunk.png", None, "Active", "user1", "Semi-Public", "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop", "https://www.w3schools.com/html/mov_bbb.mp4")
    ]
    cursor.executemany("INSERT INTO Movie VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", mock_movies)
    
    # Insert initial user behavior with group mappings
    initial_behaviors = [
        # user1 behaviors
        ("user1", 1, "view", None, 1),
        ("user1", 1, "rate", 5, 1),
        ("user1", 2, "view", None, 1),
        ("user1", 2, "rate", 4, 1),
        ("user1", 4, "view", None, 2),
        ("user1", 4, "rate", 5, 2),
        
        # user2 behaviors
        ("user2", 3, "view", None, 1),
        ("user2", 3, "rate", 5, 1),
        ("user2", 5, "view", None, 1),
        ("user2", 5, "rate", 3, 1),
        
        # user3 behaviors (Group 2 Comedy, Group 3 Thriller)
        ("user3", 4, "view", None, 2),
        ("user3", 4, "rate", 5, 2),
        ("user3", 10, "view", None, 2),
        ("user3", 10, "rate", 5, 2),
        ("user3", 5, "view", None, 3),
        ("user3", 5, "rate", 5, 3),
        ("user3", 9, "view", None, 3),
        ("user3", 9, "rate", 4, 3),
        
        # user4 behaviors (Group 1 Sci-Fi, Group 3 Thriller)
        ("user4", 1, "view", None, 1),
        ("user4", 1, "rate", 5, 1),
        ("user4", 7, "view", None, 1),
        ("user4", 7, "rate", 5, 1),
        ("user4", 9, "view", None, 3),
        ("user4", 9, "rate", 5, 3),
        
        # user5 behaviors (Group 4 Fantasy)
        ("user5", 6, "view", None, 4),
        ("user5", 6, "rate", 5, 4),
        ("user5", 8, "view", None, 4),
        ("user5", 8, "rate", 5, 4)
    ]
    cursor.executemany("INSERT INTO User_Behavior (username, movie_id, behavior_type, rating, group_id) VALUES (?, ?, ?, ?, ?)", initial_behaviors)
    
    # Insert default group movies mapping
    default_group_movies = [
        # Group 1 (電影研究社): Movie 1, 2, 7, 11, 13, 16, 17
        (1, 1), (1, 2), (1, 7), (1, 11), (1, 13), (1, 16), (1, 17),
        # Group 2 (搞笑短影音同好會): Movie 4, 10, 14
        (2, 4), (2, 10), (2, 14),
        # Group 3 (驚悚懸疑同好會): Movie 5, 9, 15
        (3, 5), (3, 9), (3, 15),
        # Group 4 (動漫與奇幻世界): Movie 6, 8, 12
        (4, 6), (4, 8), (4, 12)
    ]
    cursor.executemany("INSERT INTO Group_Movies (group_id, movie_id, status, shared_by) VALUES (?, ?, 'Active', 'system')", default_group_movies)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
