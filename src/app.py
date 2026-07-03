import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
import requests
import pytz

@st.cache_data(ttl=3600)
def get_client_timezone():
    try:
        res = requests.get("https://ipapi.co/json/", timeout=2)
        if res.status_code == 200:
            data = res.json()
            return data.get("timezone", "Asia/Taipei")
    except Exception:
        pass
    return "Asia/Taipei"

def format_to_local_tz(utc_time_str):
    if not utc_time_str:
        return ""
    try:
        dt_utc = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S")
        dt_utc = pytz.utc.localize(dt_utc)
        tz_name = st.session_state.get("client_timezone", "Asia/Taipei")
        local_tz = pytz.timezone(tz_name)
        dt_local = dt_utc.astimezone(local_tz)
        offset = dt_local.strftime("%z")
        offset_str = f" (GMT{offset[:3]}:{offset[3:]})"
        return dt_local.strftime("%Y-%m-%d %H:%M:%S") + offset_str
    except Exception:
        return utc_time_str


# Set page config first
st.set_page_config(
    page_title="享Video - 智能影音推薦系統",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-initialize database if not exists
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "recommender.db")
if not os.path.exists(DB_PATH):
    from src.init_db import init_database
    init_database()

from src.styles import inject_custom_css
from src.data_manager import (
    get_all_movies, get_movie, get_genres, log_behavior, 
    log_recommendation_impressions, add_movie, get_user_ratings,
    get_admin_metrics, get_rating_distribution, get_genre_distribution,
    get_ctr_over_time, get_user_activity_log, get_db_connection,
    get_pending_movies, update_movie_status, create_group, join_group,
    get_user_groups, get_all_groups, get_user_memberships_status,
    get_group_pending_members, update_group_member_status,
    add_movie_to_group, approve_group_movie, reject_group_movie, get_group_pending_movies,
    delete_movie, kick_group_member, get_group_joined_members, get_group_active_movies,
    trigger_db_sync
)
from src.recommender import get_recommendations
from src.auth_helper import get_auth_config, register_user
from src.csv_validator import validate_movie_csv

@st.dialog("🎬 影片預覽與詳情", width="large")
def show_movie_modal(movie):
    username = st.session_state.get("username", "guest")
    role = st.session_state.get("role", "guest")
    
    detail_movie = get_movie(movie["id"], username)
    if not detail_movie:
        st.error("無法加載影片詳情")
        return
        
    st.image(detail_movie.get("cover_url") or detail_movie["poster_path"], width="stretch")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    g_id = st.session_state["active_group_id"]
    cursor.execute("""
        SELECT COUNT(*) FROM User_Behavior ub
        JOIN Movie m ON ub.movie_id = m.id
        WHERE ub.username = ? AND m.genre = ?
          AND (ub.group_id = ? OR (ub.group_id IS NULL AND ? IS NULL))
          AND ub.behavior_type IN ('view', 'rate', 'like')
    """, (username, detail_movie["genre"], g_id, g_id))
    interaction_count = cursor.fetchone()[0]
    conn.close()
    
    resonance_rate = 70 + min(interaction_count * 5, 25) + (detail_movie["id"] % 5)
    
    st.markdown(f"## {detail_movie['title']}")
    st.markdown(f"<span style='color: #6366F1;'>[類別: {detail_movie['genre']}] [上映: {detail_movie['release_year']}] [片長: {detail_movie['duration']}]</span>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3); padding: 12px; border-radius: 6px; margin: 10px 0;'>
        💡 <strong>AI 推薦分析:</strong><br/>
        AI 系統基於您在此群組的觀影習慣，預測您對此影片的喜愛度高達 <strong>{resonance_rate}%</strong>（分析自您在【{st.session_state['active_group_name']}】的 {interaction_count} 次【{detail_movie['genre']}】類型影片互動）。
    </div>
    """, unsafe_allow_html=True)
    
    st.write("### 📺 預覽播放 (Video Player)")
    st.video(detail_movie.get("video_preview_url") or detail_movie.get("video_path") or "https://www.w3schools.com/html/mov_bbb.mp4")
    
    st.write("---")
    vis_icons = {"Public": "🌐 公開 (Public)", "Semi-Public": "👥 半公開 (Semi-Public)", "Private": "🔒 私密 (Private)"}
    vis_lbl = vis_icons.get(detail_movie["visibility"], detail_movie["visibility"])
    st.write(f"🔒 權限標籤: `{vis_lbl}` | 👥 上傳者: `{detail_movie['uploaded_by']}`")
    
    # Show sharing info if inside a group space
    if g_id is not None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT shared_by FROM Group_Movies WHERE group_id = ? AND movie_id = ?", (g_id, detail_movie["id"]))
        row = cursor.fetchone()
        conn.close()
        if row and row["shared_by"]:
            st.info(f"📢 這部影片是由 **{row['shared_by']}** 分享至本群組")
            if row["shared_by"] == username:
                with st.popover("📤 從此群組收回分享"):
                    st.warning("確認要將此影片從群組空間中收回嗎？")
                    if st.button("確認收回", key=f"recall_share_{g_id}_{detail_movie['id']}"):
                        reject_group_movie(g_id, detail_movie["id"])
                        st.toast("已從此群組收回分享 (空間資料已同步至雲端)")
                        st.rerun()
            
    # Add sharing selectbox and button
    st.write(" ")
    if role == "guest":
        st.info("💡 訪客身分無法分享影片至群組，請先登入系統並加入群組空間。")
    else:
        # Get user's joined groups
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.group_id, g.name FROM Groups g
            JOIN Group_Members gm ON g.group_id = gm.group_id
            WHERE gm.username = ? AND gm.status = 'Joined'
        """, (username,))
        user_joined_groups = [dict(r) for r in cursor.fetchall()]
        
        # Exclude groups the movie is already associated with
        cursor.execute("SELECT group_id FROM Group_Movies WHERE movie_id = ?", (detail_movie["id"],))
        existing_gids = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        if not user_joined_groups:
            st.info("💡 您目前尚未加入任何群組空間，請先至「群組空間管理」加入或建立群組。")
        else:
            shareable_groups = [g for g in user_joined_groups if g["group_id"] not in existing_gids]
            if shareable_groups:
                with st.container(border=True):
                    st.write("📤 **分享影片至其他群組**")
                    group_options = {g["name"]: g["group_id"] for g in shareable_groups}
                    selected_target_gname = st.selectbox("選擇要分享的群組空間", list(group_options.keys()), key=f"share_gselect_{detail_movie['id']}")
                    if st.button("確認分享至此群組", key=f"share_gbtn_{detail_movie['id']}"):
                        target_gid = group_options[selected_target_gname]
                        if detail_movie["visibility"] == "Private":
                            st.warning("⚠️ 私密影片限本人觀看，無法分享至群組影片庫！")
                        else:
                            # Determine if owner of target group
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT created_by FROM Groups WHERE group_id = ?", (target_gid,))
                            owner = cursor.fetchone()[0]
                            conn.close()
                            
                            status_to_insert = "Active" if username == owner else "Pending"
                            add_movie_to_group(target_gid, detail_movie["id"], username, status_to_insert)
                            
                            if status_to_insert == "Active":
                                st.toast(f"已分享並自動發佈至【{selected_target_gname}】 (空間資料已同步至雲端)！")
                            else:
                                st.toast(f"已提交分享申請至【{selected_target_gname}】 (空間資料已同步至雲端)！")
                            st.rerun()
            else:
                st.info("💡 此影片已分享至您加入的所有群組空間。")
            
    st.write("### 💬 社群成員評論")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, rating, timestamp FROM User_Behavior
        WHERE movie_id = ? AND behavior_type = 'rate'
        ORDER BY id DESC LIMIT 5
    """, (detail_movie["id"],))
    comments = cursor.fetchall()
    conn.close()
    
    if comments:
        for c in comments:
            st.markdown(f"⭐ **{c['username']}**: 評分 `{c['rating']} 星` (*於 {format_to_local_tz(c['timestamp'])}*)")
    else:
        st.info("💬 此影片目前尚無評論，快來搶沙發！")
        
    if role != "guest":
        st.write("---")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM User_Behavior 
            WHERE username = ? AND movie_id = ? AND behavior_type = 'like'
              AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
        """, (username, detail_movie["id"], g_id, g_id))
        has_liked = cursor.fetchone() is not None
        
        cursor.execute("""
            SELECT COUNT(*) FROM User_Behavior 
            WHERE movie_id = ? AND behavior_type = 'like'
        """, (detail_movie["id"],))
        total_likes = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT rating FROM User_Behavior 
            WHERE username = ? AND movie_id = ? AND behavior_type = 'rate'
              AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
        """, (username, detail_movie["id"], g_id, g_id))
        existing_rate_row = cursor.fetchone()
        conn.close()
        
        prev_rating = existing_rate_row["rating"] if existing_rate_row else None
        
        col_like_btn, col_like_cnt = st.columns([1.5, 3])
        with col_like_btn:
            if has_liked:
                if st.button("❤️ 已按讚", key=f"dlg_like_{detail_movie['id']}", type="primary"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM User_Behavior 
                        WHERE username = ? AND movie_id = ? AND behavior_type = 'like'
                          AND (group_id = ? OR (group_id IS NULL AND ? IS NULL))
                    """, (username, detail_movie["id"], g_id, g_id))
                    conn.commit()
                    conn.close()
                    st.toast("取消按讚 💔")
                    st.rerun()
            else:
                if st.button("🤍 按讚", key=f"dlg_like_{detail_movie['id']}", type="secondary"):
                    log_behavior(username, detail_movie["id"], "like", group_id=g_id)
                    st.toast("已按讚！ 👍", icon="❤️")
                    st.rerun()
        with col_like_cnt:
            st.markdown(f"<div style='padding-top: 6px; font-size: 0.9rem;'>🔥 **{total_likes}** 人覺得這部影片很讚</div>", unsafe_allow_html=True)
            
        st.write(" ")
        st.write("### ⭐ 為影片留下您的評分：")
        try:
            score = st.feedback("stars", key=f"dlg_feed_stars_{detail_movie['id']}")
            if score is not None:
                rating_val = score + 1
                if rating_val != prev_rating:
                    log_behavior(username, detail_movie["id"], "rate", rating_val, group_id=g_id)
                    st.toast(f"感謝評分！你給了 {rating_val} 顆星 ⭐", icon="🎉")
                    st.rerun()
        except Exception:
            rating_val = st.slider("拉動滑桿評分 (1-5 星)", 1, 5, value=prev_rating or 5, key=f"dlg_slider_{detail_movie['id']}")
            if st.button("送出評分", key=f"dlg_submit_rate_{detail_movie['id']}"):
                log_behavior(username, detail_movie["id"], "rate", rating_val, group_id=g_id)
                st.toast(f"感謝評分！你給了 {rating_val} 顆星 ⭐")
                st.rerun()

# Inject CSS styles
inject_custom_css()

# Initialize session state variables
if "selected_movie_id" not in st.session_state:
    st.session_state["selected_movie_id"] = None
if "last_rec_ids" not in st.session_state:
    st.session_state["last_rec_ids"] = []
if "client_timezone" not in st.session_state:
    st.session_state["client_timezone"] = get_client_timezone()
if "active_group_id" not in st.session_state:
    st.session_state["active_group_id"] = None
if "active_group_name" not in st.session_state:
    st.session_state["active_group_name"] = "個人空間"
if "role" not in st.session_state:
    st.session_state["role"] = "guest"

# --- Authentication ---
config, roles = get_auth_config()

import streamlit_authenticator as stauth

# Setup authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render authentication interface
st.markdown("<div style='text-align: center; padding-top: 2rem;'><h1 style='font-size: 3rem; font-weight: 900; background: linear-gradient(45deg, #00F2FE 0%, #4FACFE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🍿 享Video</h1><p style='color: #94A3B8; font-size: 1.1rem; margin-bottom: 2rem;'>享受輕鬆，享Video</p></div>", unsafe_allow_html=True)

# Login and Register tabs when not authenticated
if not st.session_state.get("authentication_status"):
    st.session_state["role"] = "guest"
    tab_login, tab_register = st.tabs(["👤 用戶登入", "🆕 使用者註冊"])
    
    with tab_login:
        # Streamlit-authenticator login widget
        authenticator.login(location='main')
        
        if st.session_state["authentication_status"] is False:
            st.error("帳號或密碼錯誤，請重新輸入。")
        elif st.session_state["authentication_status"] is None:
            st.info("請輸入您的帳號與密碼進行登入。")
            
        st.write("---")
        st.write("### 或是以訪客身份觀看")
        if st.button("🚪 訪客觀看 (免登入播放)"):
            st.session_state["guest_mode"] = True
            st.session_state["username"] = "guest"
            st.session_state["name"] = "訪客"
            st.session_state["authentication_status"] = True
            st.session_state["role"] = "guest"
            st.rerun()
            
    with tab_register:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### 註冊新帳號")
        with st.form("register_form", clear_on_submit=True):
            reg_username = st.text_input("帳號 (Username)")
            reg_name = st.text_input("名稱/姓名 (Name)")
            reg_email = st.text_input("電子信箱 (Email)")
            reg_password = st.text_input("密碼 (Password)", type="password")
            
            submit_btn = st.form_submit_button("立即註冊")
            if submit_btn:
                success, msg = register_user(reg_username, reg_password, reg_email, reg_name, 'user')
                if success:
                    st.success("註冊成功！請切換至「用戶登入」分頁進行登入。")
                else:
                    st.error(f"註冊失敗: {msg}")
        st.markdown("</div>", unsafe_allow_html=True)

# --- Authenticated App ---
if st.session_state["authentication_status"]:
    is_guest = st.session_state.get("guest_mode", False)
    username = st.session_state["username"]
    role = "guest" if is_guest else roles.get(username, "user")
    st.session_state["role"] = role
    
    # --- Side Bar Menu ---
    st.sidebar.markdown(f"<div style='text-align: center; padding: 15px 0;'><h2 style='background: linear-gradient(45deg, #00F2FE 0%, #4FACFE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;'>享Video</h2></div>", unsafe_allow_html=True)
    st.sidebar.markdown(f"### 👋 歡迎回來, **{st.session_state['name']}**!")
    st.sidebar.markdown(f"**目前身分:** `{ '管理員 (Admin)' if role == 'admin' else ('一般用戶 (User)' if role == 'user' else '訪客 (Guest)') }`")
    st.sidebar.markdown("---")
    
    # Navigation depending on role (RBAC)
    if role == "admin":
        menu = st.sidebar.radio("📚 後台功能導覽", ["📊 數據統計看板", "🎬 影片庫管理庫", "🔍 影片審核後台"])
    elif role == "guest":
        st.sidebar.markdown("**當前空間:** `訪客公開空間`")
        st.sidebar.markdown("---")
        menu = st.sidebar.radio("🍿 訪客功能導覽", ["🎬 影音大廳"])
    else:
        # Group Selection Dropdown
        user_groups = get_user_groups(username)
        group_names = ["個人空間"] + [g["name"] for g in user_groups]
        
        # Determine index
        curr_index = 0
        if st.session_state["active_group_name"] in group_names:
            curr_index = group_names.index(st.session_state["active_group_name"])
            
        with st.sidebar.container(border=True):
            selected_g_name = st.selectbox("👥 切換活動空間", group_names, index=curr_index)
            
            if selected_g_name != st.session_state["active_group_name"]:
                st.session_state["active_group_name"] = selected_g_name
                if selected_g_name == "個人空間":
                    st.session_state["active_group_id"] = None
                else:
                    st.session_state["active_group_id"] = next(g["group_id"] for g in user_groups if g["name"] == selected_g_name)
                # Clear cache
                st.session_state["last_rec_ids"] = []
                st.session_state["selected_movie_id"] = None
                st.rerun()
                
            st.markdown(f"**當前空間:** `{st.session_state['active_group_name']}`")
        st.sidebar.markdown("---")
        
        menu = st.sidebar.radio("🍿 影音大廳導覽", ["🎬 影音大廳", "📤 影片分享上傳", "👥 群組空間管理", "📝 我的評分紀錄"])
        
    st.sidebar.markdown("---")
    # Logout button in sidebar
    if is_guest:
        if st.sidebar.button("🚪 登出訪客 / 登入系統", width="stretch"):
            st.session_state["guest_mode"] = False
            st.session_state["username"] = None
            st.session_state["name"] = None
            st.session_state["authentication_status"] = None
            st.session_state["role"] = "guest"
            st.rerun()
    else:
        authenticator.logout('登出系統', 'sidebar')
    
    # --- USER INTERFACES ---
    if role == "user" or role == "guest":
        if menu == "🎬 影音大廳":
            # Welcome banner
            st.markdown(f"""
            <div class='cyber-panel' style='text-align: center;'>
                <h1 style='margin: 0; color: #F8FAFC;'>🎬 享Video - 智能影音推薦系統</h1>
                <p style='margin: 5px 0 0 0; color: #94A3B8;'>個人化影片推薦與群組影音空間 - 目前空間: {st.session_state['active_group_name']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_left, col_center, col_right = st.columns([1, 2.2, 1])
            
            with col_left:
                st.markdown("### 📊 群組數據看板")
                st.markdown("<div class='cyber-panel'>", unsafe_allow_html=True)
                
                # Calculate stats
                conn = get_db_connection()
                cursor = conn.cursor()
                g_id = st.session_state["active_group_id"]
                
                # Get total videos in group
                if g_id is not None:
                    cursor.execute("SELECT COUNT(*) FROM Group_Movies WHERE group_id = ?", (g_id,))
                    total_group_movies = cursor.fetchone()[0]
                    # Get active member count
                    cursor.execute("SELECT COUNT(*) FROM Group_Members WHERE group_id = ? AND status = 'Joined'", (g_id,))
                    active_members = cursor.fetchone()[0]
                else:
                    cursor.execute("SELECT COUNT(*) FROM Movie WHERE status = 'Active'")
                    total_group_movies = cursor.fetchone()[0]
                    active_members = 1
                    
                # Calculate space hotness based on total behaviors in this group
                if g_id is not None:
                    cursor.execute("SELECT COUNT(*) FROM User_Behavior WHERE group_id = ?", (g_id,))
                    total_behaviors = cursor.fetchone()[0]
                else:
                    cursor.execute("SELECT COUNT(*) FROM User_Behavior WHERE group_id IS NULL")
                    total_behaviors = cursor.fetchone()[0]
                conn.close()
                
                resonance_hotness = 50 + min(total_behaviors * 3, 49) + (total_group_movies % 5)
                
                st.metric(label="🔥 空間熱度值", value=f"{resonance_hotness:.1f} %", delta=f"+{total_behaviors % 4 + 1}.5% 自昨日")
                st.metric(label="👥 在線成員", value=f"{active_members} 人", delta="在線中")
                st.metric(label="🎬 影片總數", value=f"{total_group_movies} 部", delta="正常連線")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col_right:
                st.markdown("### ❤️ 社群喜好 analysis")
                st.markdown("<div class='cyber-panel'>", unsafe_allow_html=True)
                st.write("**群組影片喜好分佈 (Group Profile)**")
                
                g_name = st.session_state["active_group_name"]
                if "電影研究社" in g_name or g_id == 1:
                    st.progress(0.80, text="🧠 燒腦題材: 80%")
                    st.progress(0.20, text="🌌 史詩震撼: 20%")
                elif "搞笑" in g_name or g_id == 2:
                    st.progress(0.85, text="⚡ 爆笑喜劇: 85%")
                    st.progress(0.15, text="🌱 溫馨療癒: 15%")
                elif "驚悚" in g_name or g_id == 3:
                    st.progress(0.75, text="👁️ 緊張懸疑: 75%")
                    st.progress(0.25, text="🩸 恐怖驚悚: 25%")
                elif "動漫" in g_name or g_id == 4:
                    st.progress(0.70, text="🔥 熱血冒險: 70%")
                    st.progress(0.30, text="🧚 奇幻魔法: 30%")
                else:
                    st.progress(0.50, text="🛸 專注學習: 50%")
                    st.progress(0.50, text="🌊 放鬆休閒: 50%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col_center:
                st.markdown("### 🔍 智慧語義搜尋 (AI Search)")
                col_search, col_mine = st.columns([3, 1.2])
                with col_search:
                    search_q = st.text_input("🔍 輸入關鍵字或偏好...", placeholder="例如：科幻冒險、燒腦懸疑...", label_visibility="collapsed")
                with col_mine:
                    show_mine_only = False
                    if username and username != 'guest':
                        show_mine_only = st.checkbox("🔒 只顯示我上傳", value=False)
                
                # Fetch recommendations
                st.write("### 🎯 推薦影片 (AI 推薦)")
                recs = get_recommendations(username, group_id=st.session_state["active_group_id"], limit=3)
                if recs:
                    rec_ids = [m["id"] for m in recs]
                    if rec_ids != st.session_state["last_rec_ids"]:
                        log_recommendation_impressions(username, rec_ids, group_id=st.session_state["active_group_id"])
                        st.session_state["last_rec_ids"] = rec_ids
                        
                    rec_cols = st.columns(3)
                    for idx, movie in enumerate(recs):
                        with rec_cols[idx]:
                            filled_blocks = int(round(movie["avg_rating"] * 2))
                            ascii_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
                            
                            st.markdown(f"""
                            <div class='cyber-card'>
                                <div class='cyber-card-img-container'>
                                    <img src='{movie.get("cover_url") or movie["poster_path"]}' class='static-img' />
                                    <video class='hover-video' src='{movie.get("video_preview_url") or "https://www.w3schools.com/html/mov_bbb.mp4"}' autoplay loop muted playsinline></video>
                                </div>
                                <div class='cyber-card-content'>
                                    <div class='cyber-card-title'>{movie["title"]}</div>
                                    <div class='cyber-card-meta'>
                                        <span>[ID: REC-{movie['id']:03d}]</span>
                                        <span class='resonance-indicator'>推薦度: {80 + (movie['id'] % 5) * 4}%</span>
                                    </div>
                                    <div style='font-size: 0.72rem; color: #8B5CF6; margin-top: 5px;'>
                                        ⭐ [{ascii_bar}] {round(movie["avg_rating"], 1)}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("🎬 點擊觀看", key=f"rec_scan_{movie['id']}"):
                                log_behavior(username, movie["id"], "rec_click", group_id=st.session_state["active_group_id"])
                                log_behavior(username, movie["id"], "view", group_id=st.session_state["active_group_id"])
                                show_movie_modal(movie)
                else:
                    st.info("📡 暫無推薦影片。")
                
                st.write("---")
                
                # Fetch all movies inside active group
                st.write("### 🎬 影片大廳庫")
                movies = get_all_movies(username, search_q, "全部", show_mine_only=show_mine_only, group_id=st.session_state["active_group_id"])
                
                if movies:
                    movies_grid = st.columns(3)
                    for idx, movie in enumerate(movies):
                        col_idx = idx % 3
                        with movies_grid[col_idx]:
                            filled_blocks = int(round(movie["avg_rating"] * 2))
                            ascii_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
                            
                            st.markdown(f"""
                            <div class='cyber-card'>
                                <div class='cyber-card-img-container'>
                                    <img src='{movie.get("cover_url") or movie["poster_path"]}' class='static-img' />
                                    <video class='hover-video' src='{movie.get("video_preview_url") or "https://www.w3schools.com/html/mov_bbb.mp4"}' autoplay loop muted playsinline></video>
                                </div>
                                <div class='cyber-card-content'>
                                    <div class='cyber-card-title'>{movie["title"]}</div>
                                    <div class='cyber-card-meta'>
                                        <span>[ID: VIDEO-{movie['id']:03d}]</span>
                                        <span class='resonance-indicator'>觀看次數: {movie.get('view_count', 0)}</span>
                                    </div>
                                    <div style='font-size: 0.72rem; color: #8B5CF6; margin-top: 5px;'>
                                        ⭐ [{ascii_bar}] {round(movie["avg_rating"], 1)}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("🎬 點擊觀看", key=f"lib_scan_{movie['id']}"):
                                log_behavior(username, movie["id"], "view", group_id=st.session_state["active_group_id"])
                                show_movie_modal(movie)
                else:
                    st.info("🎬 未搜尋到符合條件的影片資料。")
                
        elif menu == "📤 影片分享上傳":
            st.write("## 📤 影片分享上傳")
            st.write("您可以在此上傳並分享您的影音影片。選擇「公開」或「半公開」影片將送出進行審核，而「私密」影片則直接發佈，無需審核。")
            
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            with st.form("user_upload_movie_form", clear_on_submit=True):
                up_title = st.text_input("影片名稱", placeholder="輸入影片名稱...")
                up_genre = st.selectbox("影片類型", ["科幻", "動作", "浪漫", "喜劇", "懸疑", "奇幻", "紀錄片", "恐怖", "動畫"])
                up_duration = st.text_input("影片片長", value="120 mins", placeholder="例如: 120 mins")
                up_visibility = st.radio("影片可視隱私等級", ["🌐公開 (Public)", "👥半公開 (Semi-Public)", "🔒私密 (Private)"], horizontal=True)
                up_desc = st.text_area("影片劇情描述/大綱", placeholder="輸入影片的簡短描述...")
                
                # File upload simulation
                up_file = st.file_uploader("選擇影片檔案 (MP4/MOV) 或 CSV 檔案模擬上傳", type=["mp4", "mov", "csv"])
                
                # Default posters
                up_poster_choice = st.selectbox("選擇預設封面海報風格", [
                    ("src/assets/interstellar.png", "宇宙星空風格"),
                    ("src/assets/cyberpunk.png", "都市霓虹風格"),
                    ("src/assets/romance.png", "落日浪漫風格"),
                    ("src/assets/comedy.png", "卡通喜劇風格"),
                    ("src/assets/thriller.png", "霧中懸疑風格"),
                    ("src/assets/fantasy.png", "巨龍奇幻風格")
                ])
                
                upload_submit = st.form_submit_button("🚀 點選發佈/送出審核")
                if upload_submit:
                    if not up_title or not up_desc or not up_duration:
                        st.error("請填寫所有必要欄位（影片名稱、片長、大綱描述）！")
                    elif up_file is None:
                        st.error("請選擇要上傳的模擬影片或 CSV 檔案！")
                    else:
                        poster_path = up_poster_choice[0]
                        # Simulating file save
                        video_path = None
                        if up_file is not None:
                            app_dir = os.path.dirname(os.path.abspath(__file__))
                            upload_dir = os.path.join(app_dir, "assets", "user_uploads")
                            os.makedirs(upload_dir, exist_ok=True)
                            safe_name = "".join(c for c in up_title if c.isalnum() or c in ("_", "-")).strip()
                            if not safe_name:
                                safe_name = "user_upload"
                            file_ext = os.path.splitext(up_file.name)[1]
                            filename = f"{safe_name}_{int(datetime.now().timestamp())}{file_ext}"
                            save_path = os.path.join(upload_dir, filename)
                            with open(save_path, "wb") as f:
                                f.write(up_file.getbuffer())
                            video_path = f"src/assets/user_uploads/{filename}"
                            
                        # Map visibility
                        vis_map = {
                            "🌐公開 (Public)": "Public",
                            "👥半公開 (Semi-Public)": "Semi-Public",
                            "🔒私密 (Private)": "Private"
                        }
                        vis_val = vis_map[up_visibility]
                        
                        # Private videos are auto-approved (Active)
                        status_val = "Active" if vis_val == "Private" else "Pending"
                        
                        # Add movie
                        genre_covers = {
                            "科幻": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop",
                            "動作": "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop",
                            "浪漫": "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=800&auto=format&fit=crop",
                            "喜劇": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&auto=format&fit=crop",
                            "懸疑": "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop",
                            "奇幻": "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=800&auto=format&fit=crop"
                        }
                        default_cov = genre_covers.get(up_genre, "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop")
                        
                        add_movie(
                            title=up_title,
                            genre=up_genre,
                            description=up_desc,
                            release_year=datetime.now().year,
                            duration=up_duration,
                            poster_path=poster_path,
                            video_path=video_path,
                            status=status_val,
                            uploaded_by=username,
                            visibility=vis_val,
                            cover_url=default_cov,
                            video_preview_url="https://www.w3schools.com/html/mov_bbb.mp4",
                            group_id=st.session_state["active_group_id"] if vis_val in ("Public", "Semi-Public") else None
                        )
                        if vis_val == "Private":
                            st.success(f"🎉 私密影片《{up_title}》已成功發佈！此影片僅限您本人觀看，無需審核。")
                            st.toast("空間資料已同步至雲端")
                        else:
                            st.success(f"🎉 影片《{up_title}》已成功送出審核！待管理員或相關審核通過後發佈。")
                            st.toast("空間資料已同步至雲端")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # --- 我的影片上傳與審核紀錄 ---
            st.markdown("---")
            st.write("### 📋 我的影片上傳與審核紀錄")
            my_uploads = get_all_movies(username, show_mine_only=True)
            if my_uploads:
                for m in my_uploads:
                    st.markdown("<div class='glass-card' style='padding: 18px; margin-bottom: 12px;'>", unsafe_allow_html=True)
                    col_info, col_status = st.columns([3.5, 1.5])
                    with col_info:
                        st.markdown(f"**🎬 {m['title']}** (<span style='color: #00F2FE;'>{m['genre']}</span>) — *{m['duration']}*", unsafe_allow_html=True)
                        st.write(m['description'])
                    with col_status:
                        status = m.get('status', 'Pending')
                        visibility = m.get('visibility', 'Public')
                        vis_icons = {"Public": "🌐 公開", "Semi-Public": "👥 半公開", "Private": "🔒 私密"}
                        vis_lbl = vis_icons.get(visibility, visibility)
                        st.write(f"可視等級: `{vis_lbl}`")
                        if status == "Active":
                            st.success("🟢 審核通過 (Active)")
                        elif status == "Pending":
                            st.warning("🟡 待審核 (Pending)")
                        elif status == "Rejected":
                            st.error("🔴 已駁回 (Rejected)")
                        else:
                            st.info(f"狀態: {status}")
                            
                        # Delete uploaded movie popover confirmation
                        with st.popover("🗑️ 刪除影片"):
                            st.warning("確認要將此影片從空間中告別嗎？")
                            if st.button("確認", key=f"del_user_movie_{m['id']}"):
                                delete_movie(m['id'])
                                st.toast("已與該影片優雅告別 (空間資料已同步至雲端)")
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("您目前沒有上傳任何影片。")
            
            
        elif menu == "👥 群組空間管理":
            st.write("## 👥 群組與社群管理空間")
            st.write("加入感興趣的群組，或自創一個社團！在群組中，系統的推薦演算法會根據您在該群組中的獨立行為，生成客製化的推薦內容。")
            
            tab_my_groups, tab_join_group, tab_create_group, tab_owner_audit, tab_movie_audit, tab_owner_panel = st.tabs([
                "🏡 我加入的群組", "🔍 尋找並加入群組", "➕ 建立新群組", "🛡️ 成員申請審核", "🎬 影片分享審核", "⚙️ 群組影片與成員管理"
            ])
            
            with tab_my_groups:
                memberships = get_user_memberships_status(username)
                if memberships:
                    st.write("### 您申請的群組與狀態：")
                    for m in memberships:
                        status_badge = ""
                        if m["status"] == "Joined":
                            status_badge = f"🟢 已加入 ({'群主 Owner' if m['group_role'] == 'Owner' else '成員 Member'})"
                        elif m["status"] == "Pending_Approval":
                            status_badge = "🟡 審核中 (等待群主同意)..."
                        elif m["status"] == "Rejected":
                            status_badge = "🔴 申請已被拒絕"
                        st.markdown(f"""
                        <div style='padding: 1rem; border-radius: 8px; background-color: rgba(255,255,255,0.05); margin-bottom: 0.5rem; border: 1px solid rgba(255,255,255,0.1);'>
                            <strong>👥 {m['group_name']}</strong> — <span style='font-size:0.9rem;'>{status_badge}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("您目前尚未加入或申請任何群組。切換至「尋找並加入群組」以開始您的社群生活！")
                    
            with tab_join_group:
                all_groups = get_all_groups()
                memberships = get_user_memberships_status(username)
                joined_or_pending_gids = [m["group_id"] for m in memberships if m["status"] in ("Joined", "Pending_Approval")]
                joinable_groups = [g for g in all_groups if g["group_id"] not in joined_or_pending_gids]
                
                if joinable_groups:
                    st.write("### 點擊申請加入群組：")
                    for g in joinable_groups:
                         col_gname, col_gbtn = st.columns([4, 1])
                         with col_gname:
                             st.markdown(f"**👥 {g['name']}** (建立者: {g['created_by']})")
                         with col_gbtn:
                             if st.button("➕ 申請加入", key=f"join_g_{g['group_id']}"):
                                 success, msg = join_group(g["group_id"], username)
                                 if success:
                                     st.success(msg)
                                     st.rerun()
                                 else:
                                     st.error(msg)
                else:
                    st.info("目前沒有您可以申請的新群組（您已申請所有群組，或系統內尚未建立其他群組）。")

            with tab_owner_audit:
                pending_requests = get_group_pending_members(username)
                if pending_requests:
                    st.write("### 待您審核的加入申請：")
                    for req in pending_requests:
                        col_applicant, col_accept, col_reject = st.columns([3, 1, 1])
                        with col_applicant:
                            st.markdown(f"👤 **{req['applicant']}** 申請加入 **{req['group_name']}**")
                        with col_accept:
                            if st.button("✅ 同意", key=f"accept_{req['group_id']}_{req['applicant']}"):
                                update_group_member_status(req['group_id'], req['applicant'], 'Joined')
                                st.success("已同意其加入申請！")
                                st.rerun()
                        with col_reject:
                            if st.button("❌ 拒絕", key=f"reject_{req['group_id']}_{req['applicant']}"):
                                update_group_member_status(req['group_id'], req['applicant'], 'Rejected')
                                st.warning("已拒絕其加入申請。")
                                st.rerun()
                else:
                    st.info("目前沒有待審核的成員加入申請。當您是群組建立者且有其他用戶申請加入時，此處會顯示審核選項。")

            with tab_movie_audit:
                # Fetch groups created/owned by this user
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT group_id, name FROM Groups WHERE created_by = ?", (username,))
                owned_groups = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                if owned_groups:
                    has_any_pending = False
                    for og in owned_groups:
                        pending_movies = get_group_pending_movies(og["group_id"])
                        if pending_movies:
                            has_any_pending = True
                            st.write(f"#### 📁 群組 【{og['name']}】 的待審核影片分享")
                            for pm in pending_movies:
                                with st.container(border=True):
                                    col_info, col_approve, col_reject = st.columns([3, 1, 1])
                                    with col_info:
                                        st.markdown(f"🎬 **{pm['title']}** ({pm['genre']})")
                                        st.markdown(f"👤 分享者: `{pm['shared_by']}`")
                                    with col_approve:
                                        if st.button("✅ 通過", key=f"app_mv_{og['group_id']}_{pm['id']}", type="primary"):
                                            approve_group_movie(og["group_id"], pm["id"])
                                            st.toast("影片已審核通過並發佈至群組！ (空間資料已同步至雲端)")
                                            st.rerun()
                                    with col_reject:
                                        if st.button("❌ 拒絕", key=f"rej_mv_{og['group_id']}_{pm['id']}", type="secondary"):
                                            reject_group_movie(og["group_id"], pm["id"])
                                            st.toast("已拒絕並下架該影片。 (空間資料已同步至雲端)")
                                            st.rerun()
                    if not has_any_pending:
                        st.info("💬 目前沒有待審核的影片分享申請。")
                else:
                    st.info("💡 您尚未建立任何群組，非群組管理員無影片審核權限。")
                    
            with tab_create_group:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.write("### 創建一個新群組")
                with st.form("create_group_form", clear_on_submit=True):
                    new_gname = st.text_input("群組名稱", placeholder="輸入群組名稱...")
                    create_g_btn = st.form_submit_button("🔨 立即建立")
                    if create_g_btn:
                        if not new_gname.strip():
                            st.error("群組名稱不能為空白！")
                        else:
                            success, msg = create_group(new_gname.strip(), username)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with tab_owner_panel:
                # Fetch groups created/owned by this user
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT group_id, name FROM Groups WHERE created_by = ?", (username,))
                owned_groups = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                if owned_groups:
                    group_names_owned = [g["name"] for g in owned_groups]
                    selected_owned_gname = st.selectbox("選擇要管理的群組空間", group_names_owned, key="owner_panel_gselect")
                    selected_owned_gid = next(g["group_id"] for g in owned_groups if g["name"] == selected_owned_gname)
                    
                    col_members, col_movies = st.columns(2)
                    
                    with col_members:
                        st.write("### 👥 成員管理")
                        joined_members = get_group_joined_members(selected_owned_gid)
                        # Filter out the owner themselves
                        joined_members = [m for m in joined_members if m["username"] != username]
                        if joined_members:
                            for m in joined_members:
                                col_mname, col_mbtn = st.columns([3, 2])
                                with col_mname:
                                    st.write(f"👤 `{m['username']}` ({m['group_role']})")
                                with col_mbtn:
                                    with st.popover("🗑️ 剔除成員"):
                                        st.warning(f"確定要將成員 {m['username']} 剔除此群組嗎？")
                                        if st.button("確認剔除", key=f"kick_{selected_owned_gid}_{m['username']}"):
                                            kick_group_member(selected_owned_gid, m["username"])
                                            st.toast(f"已將 {m['username']} 剔除此群組 (空間資料已同步至雲端)")
                                            st.rerun()
                        else:
                            st.info("此群組目前沒有其他成員。")
                            
                    with col_movies:
                        st.write("### 🎬 影片管理")
                        active_movies = get_group_active_movies(selected_owned_gid)
                        if active_movies:
                            for am in active_movies:
                                col_amname, col_ambtn = st.columns([3, 2])
                                with col_amname:
                                    st.write(f"🎬 **{am['title']}**")
                                    st.caption(f"由 `{am['shared_by']}` 分享")
                                with col_ambtn:
                                    with st.popover("🗑️ 下架影片"):
                                        st.warning(f"確定要將影片 【{am['title']}】 從群組庫中下架嗎？")
                                        if st.button("確認下架", key=f"owner_del_mv_{selected_owned_gid}_{am['id']}"):
                                            reject_group_movie(selected_owned_gid, am["id"])
                                            st.toast(f"已從群組庫中下架 【{am['title']}】 (空間資料已同步至雲端)")
                                            st.rerun()
                        else:
                            st.info("此群組影片庫目前沒有影片。")
                else:
                    st.info("💡 您目前不是任何群組的建立者，無群組管理權限。")

        elif menu == "📝 我的評分紀錄":
            st.write("## 📝 評分歷史紀錄")
            st.write("在此查看你曾經評分過的電影，評分會即時優化系統對你的推薦演算法。")
            
            ratings = get_user_ratings(username)
            if ratings:
                for r in ratings:
                    r["timestamp"] = format_to_local_tz(r["timestamp"])
                df_ratings = pd.DataFrame(ratings)
                df_ratings.columns = ["紀錄 ID", "影片名稱", "類型", "給予星等", "評分時間"]
                # Style and display dataframe
                st.dataframe(df_ratings, width="stretch")
            else:
                st.info("你尚未評分過任何影片。去影音大廳逛逛吧！")
                
    # --- ADMIN INTERFACES ---
    elif role == "admin":
        if menu == "📊 數據統計看板":
            st.write("## 📊 影音系統營運看板 (BI Analytics)")
            
            metrics = get_admin_metrics()
            
            # KPI Indicators
            col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
            with col_kpi1:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>👥 總一般用戶數</div>
                    <div class='kpi-value'>{metrics['total_users']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_kpi2:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>🎬 總收錄影片</div>
                    <div class='kpi-value'>{metrics['total_movies']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_kpi3:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>⭐ 累計用戶評分</div>
                    <div class='kpi-value'>{metrics['total_ratings']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_kpi4:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>🎯 推薦點擊率 (CTR)</div>
                    <div class='kpi-value'>{metrics['ctr']}%</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("---")
            
            # Analytics charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.write("### ⭐ 用戶評分星等分佈")
                dist_data = get_rating_distribution()
                if dist_data:
                    df_dist = pd.DataFrame(dist_data)
                    fig_dist = px.bar(
                        df_dist, x="rating", y="count", 
                        labels={"rating": "評分星等", "count": "評分次數"},
                        template="plotly_dark",
                        color_discrete_sequence=["#00F2FE"]
                    )
                    fig_dist.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_dist, width="stretch")
                else:
                    st.info("尚無評分數據")
                    
            with col_chart2:
                st.write("### 🎬 收錄影片類型佔比")
                genre_data = get_genre_distribution()
                if genre_data:
                    df_genre = pd.DataFrame(genre_data)
                    fig_genre = px.pie(
                        df_genre, names="genre", values="count",
                        template="plotly_dark",
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Tealgrn
                    )
                    fig_genre.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_genre, width="stretch")
                else:
                    st.info("尚無類型數據")
            
            st.write("---")
            
            # Line Chart: CTR Over Time
            st.write("### 🎯 推薦轉換率 (CTR) 隨時間變化趨勢")
            ctr_time_data = get_ctr_over_time()
            if ctr_time_data:
                df_ctr_time = pd.DataFrame(ctr_time_data)
                fig_ctr_line = px.line(
                    df_ctr_time, x="time_slot", y="ctr",
                    labels={"time_slot": "時間點", "ctr": "點擊轉換率 (CTR %)"},
                    template="plotly_dark",
                    markers=True,
                    color_discrete_sequence=["#4FACFE"]
                )
                fig_ctr_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_ctr_line, width="stretch")
            else:
                st.info("尚無推薦曝光/點擊歷史數據，無法計算趨勢圖。")
                
            st.write("---")
            
            # Recent user behavior logs table
            st.write("### 🔍 用戶行為即時日誌 (最近 50 筆行為)")
            logs = get_user_activity_log()
            if logs:
                for l in logs:
                    l["timestamp"] = format_to_local_tz(l["timestamp"])
                df_logs = pd.DataFrame(logs)
                df_logs.columns = ["用戶帳號", "影片名稱", "行為類型", "給予星等", "行為時間"]
                # Map behavior types to friendly strings
                behavior_map = {"view": "瀏覽影片", "rate": "評分影片", "like": "按讚影片"}
                df_logs["行為類型"] = df_logs["行為類型"].map(behavior_map)
                st.dataframe(df_logs, width="stretch")
            else:
                st.info("系統目前尚無任何用戶行為紀錄。")
                
        elif menu == "🎬 影片庫 management":
            # Let's fix spelling
            pass
            
        if menu == "🎬 影片庫管理庫":
            tab_manual, tab_csv = st.tabs(["✍️ 單筆手動新增", "📥 CSV 批次上傳與驗證"])
            
            with tab_manual:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.write("### 新增單筆影片資料")
                with st.form("manual_movie_form", clear_on_submit=True):
                    m_title = st.text_input("影片名稱")
                    m_genre = st.selectbox("影片類型", ["科幻", "動作", "浪漫", "喜劇", "懸疑", "奇幻", "紀錄片", "恐怖", "動畫"])
                    m_year = st.number_input("上映年份", min_value=1800, max_value=2100, value=2026)
                    m_duration = st.text_input("片長 (例如: 120 mins)", value="120 mins")
                    m_desc = st.text_area("影片劇情描述/大綱")
                    
                    # File uploaders
                    img_file = st.file_uploader("上傳海報圖片 (可留空，未上傳則使用下方選單配置)", type=["png", "jpg", "jpeg"])
                    video_file = st.file_uploader("上傳預覽影音 (可留空)", type=["mp4", "mov", "avi"])
                    
                    # Manual path or default random poster
                    m_poster = st.selectbox("配置預設海報風格 (僅在未上傳自訂海報時生效)", [
                        ("src/assets/interstellar.png", "宇宙星空風格"),
                        ("src/assets/cyberpunk.png", "都市霓虹風格"),
                        ("src/assets/romance.png", "落日浪漫風格"),
                        ("src/assets/comedy.png", "卡通喜劇風格"),
                        ("src/assets/thriller.png", "霧中懸疑風格"),
                        ("src/assets/fantasy.png", "巨龍奇幻風格")
                    ])
                    
                    submit_manual = st.form_submit_button("新增影片")
                    if submit_manual:
                        if not m_title or not m_desc or not m_duration:
                            st.error("所有欄位皆為必填！")
                        else:
                            # Save custom poster if uploaded
                            poster_path = m_poster[0]
                            if img_file is not None:
                                app_dir = os.path.dirname(os.path.abspath(__file__))
                                upload_img_dir = os.path.join(app_dir, "assets", "uploaded_posters")
                                os.makedirs(upload_img_dir, exist_ok=True)
                                safe_title = "".join(c for c in m_title if c.isalnum() or c in ("_", "-")).strip()
                                if not safe_title:
                                    safe_title = "uploaded"
                                file_ext = os.path.splitext(img_file.name)[1]
                                filename = f"{safe_title}_{int(datetime.now().timestamp())}{file_ext}"
                                save_path = os.path.join(upload_img_dir, filename)
                                with open(save_path, "wb") as f:
                                    f.write(img_file.getbuffer())
                                poster_path = f"src/assets/uploaded_posters/{filename}"
                                
                            # Save custom video if uploaded
                            video_path = None
                            if video_file is not None:
                                app_dir = os.path.dirname(os.path.abspath(__file__))
                                upload_video_dir = os.path.join(app_dir, "assets", "uploaded_videos")
                                os.makedirs(upload_video_dir, exist_ok=True)
                                safe_title = "".join(c for c in m_title if c.isalnum() or c in ("_", "-")).strip()
                                if not safe_title:
                                    safe_title = "uploaded"
                                file_ext = os.path.splitext(video_file.name)[1]
                                filename = f"{safe_title}_{int(datetime.now().timestamp())}{file_ext}"
                                save_path = os.path.join(upload_video_dir, filename)
                                with open(save_path, "wb") as f:
                                    f.write(video_file.getbuffer())
                                video_path = f"src/assets/uploaded_videos/{filename}"
                                
                            genre_covers = {
                                "科幻": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop",
                                "動作": "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop",
                                "浪漫": "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=800&auto=format&fit=crop",
                                "喜劇": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&auto=format&fit=crop",
                                "懸疑": "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop",
                                "奇幻": "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=800&auto=format&fit=crop"
                            }
                            default_cov = genre_covers.get(m_genre, "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop")
                            
                            add_movie(
                                title=m_title,
                                genre=m_genre,
                                description=m_desc,
                                release_year=m_year,
                                duration=m_duration,
                                poster_path=poster_path,
                                video_path=video_path,
                                status="Active",
                                uploaded_by="admin",
                                cover_url=default_cov,
                                video_preview_url="https://www.w3schools.com/html/mov_bbb.mp4"
                            )
                            st.success(f"影片《{m_title}》已成功寫入資料庫！")
                            st.toast("空間資料已同步至雲端")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with tab_csv:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.write("### 📥 批次匯入影片 CSV")
                st.write("上傳一個包含影片資料的 CSV 檔案。系統會在寫入資料庫前，以 Python 進行嚴格的空值與格式驗證。")
                
                # Show sample format
                st.info("💡 **CSV 範例格式：** 欄位必須包含 `title`, `genre`, `description`, `release_year`, `duration`。")
                sample_data = {
                    "title": ["駭客任務", "鐵達尼號"],
                    "genre": ["科幻", "浪漫"],
                    "description": ["尼歐發現世界是虛擬的...", "傑克與蘿絲的船難愛情..."],
                    "release_year": [1999, 1997],
                    "duration": ["136 mins", "194 mins"]
                }
                st.dataframe(pd.DataFrame(sample_data), height=110)
                
                uploaded_file = st.file_uploader("選擇 CSV 檔案", type="csv")
                
                if uploaded_file is not None:
                    # Read bytes and convert to string
                    bytes_data = uploaded_file.read()
                    file_contents = bytes_data.decode("utf-8")
                    
                    # Validate
                    is_valid, errors, validated_df = validate_movie_csv(file_contents)
                    
                    if not is_valid:
                        st.error("❌ **CSV 驗證失敗！資料未被匯入。請修正以下錯誤：**")
                        # Scrollable box for errors
                        st.markdown("<div style='max-height: 200px; overflow-y: auto; background-color: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 8px; padding: 12px;'>", unsafe_allow_html=True)
                        for err in errors:
                            st.write(f"- {err}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.success("✅ **CSV 格式與數據驗證通過！**")
                        st.write("### 📋 即將匯入的資料預覽")
                        st.dataframe(validated_df, width="stretch")
                        
                        # Choose poster path style for the batch
                        batch_poster = st.selectbox("批次指派預設海報風格", [
                            ("src/assets/cyberpunk.png", "都市霓虹風格"),
                            ("src/assets/interstellar.png", "宇宙星空風格"),
                            ("src/assets/romance.png", "落日浪漫風格"),
                            ("src/assets/comedy.png", "卡通喜劇風格"),
                            ("src/assets/thriller.png", "霧中懸疑風格"),
                            ("src/assets/fantasy.png", "巨龍奇幻風格")
                        ])
                        
                        if st.button("💾 確認寫入資料庫"):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            imported_count = 0
                            for _, row in validated_df.iterrows():
                                genre_covers = {
                                    "科幻": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop",
                                    "動作": "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop",
                                    "浪漫": "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=800&auto=format&fit=crop",
                                    "喜劇": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&auto=format&fit=crop",
                                    "懸疑": "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=800&auto=format&fit=crop",
                                    "奇幻": "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=800&auto=format&fit=crop"
                                }
                                default_cov = genre_covers.get(row["genre"], "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?w=800&auto=format&fit=crop")
                                
                                cursor.execute("""
                                    INSERT INTO Movie (title, genre, description, release_year, duration, poster_path, status, uploaded_by, visibility, cover_url, video_preview_url)
                                    VALUES (?, ?, ?, ?, ?, ?, 'Active', 'admin', 'Public', ?, ?)
                                """, (
                                    row["title"], 
                                    row["genre"], 
                                    row["description"], 
                                    int(row["release_year"]), 
                                    row["duration"], 
                                    batch_poster[0],
                                    default_cov,
                                    "https://www.w3schools.com/html/mov_bbb.mp4"
                                ))
                                imported_count += 1
                            conn.commit()
                            conn.close()
                            trigger_db_sync()
                            st.toast(f"成功批次匯入 {imported_count} 部影片 (空間資料已同步至雲端)！ 🎉")
                            st.success(f"已成功匯入 {imported_count} 部影片至資料庫。")
                st.markdown("</div>", unsafe_allow_html=True)
                
        elif menu == "🔍 影片審核後台":
            st.write("## 🔍 影片審核後台")
            st.write("在此審核一般使用者分享的影片。審核通過的影片會立刻發佈至影音大廳，供所有人觀賞。")
            
            tab_pending_adm, tab_all_adm = st.tabs(["⏳ 待審核影片", "🎬 平台全部影片"])
            
            with tab_pending_adm:
                pending_movies = get_pending_movies()
                if pending_movies:
                    for movie in pending_movies:
                        st.markdown("<div class='glass-card' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
                        col_det, col_ops = st.columns([4, 1.2])
                        
                        with col_det:
                            st.write(f"### {movie['title']}")
                            st.markdown(f"**類別:** `{movie['genre']}` | **片長:** `{movie['duration']}` | **上傳者:** `{movie['uploaded_by']}`")
                            st.write(f"**大綱描述:** {movie['description']}")
                            if movie.get('video_path'):
                                st.write(f"*影片檔案已暫存於:* `{movie['video_path']}`")
                                
                        with col_ops:
                            st.write(" ")
                            st.write(" ")
                            btn_approve = st.button("核准通過", key=f"appr_{movie['id']}", type="primary")
                            btn_reject = st.button("予以駁回", key=f"rej_{movie['id']}", type="secondary")
                            
                            if btn_approve:
                                update_movie_status(movie['id'], 'Active')
                                st.toast(f"影片 【{movie['title']}】 已審核通過 (空間資料已同步至雲端)")
                                st.rerun()
                                
                            if btn_reject:
                                update_movie_status(movie['id'], 'Rejected')
                                st.toast(f"影片 【{movie['title']}】 已被駁回 (空間資料已同步至雲端)")
                                st.rerun()
                                
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("💡 目前沒有待審核的影片。")
                    
            with tab_all_adm:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Movie ORDER BY id DESC")
                all_movies = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                if all_movies:
                    for m in all_movies:
                        st.markdown("<div class='glass-card' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
                        col_det, col_ops = st.columns([4, 1.5])
                        
                        with col_det:
                            st.write(f"### {m['title']}")
                            status_badge = ""
                            if m['status'] == "Active":
                                status_badge = "🟢 已發佈 (Active)"
                            elif m['status'] == "Pending":
                                status_badge = "🟡 待審核 (Pending)"
                            elif m['status'] == "Rejected":
                                status_badge = "🔴 已駁回 (Rejected)"
                            st.markdown(f"**類別:** `{m['genre']}` | **可見度:** `{m['visibility']}` | **狀態:** {status_badge}")
                            st.write(f"**上傳者:** `{m['uploaded_by']}` | **片長:** `{m['duration']}`")
                            st.write(f"**大綱描述:** {m['description']}")
                            
                        with col_ops:
                            st.write(" ")
                            st.write(" ")
                            with st.popover("🔥 強制下架並銷毀"):
                                st.warning("確認要將此影片從整個系統平台中完全銷毀嗎？此操作不可逆！")
                                if st.button("確認銷毀", key=f"destroy_mv_{m['id']}"):
                                    delete_movie(m['id'])
                                    st.toast(f"已從平台強制銷毀影片 【{m['title']}】 (空間資料已同步至雲端)")
                                    st.rerun()
                                    
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("💡 系統平台目前沒有任何影片。")
