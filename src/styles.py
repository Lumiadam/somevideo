import streamlit as st

def inject_custom_css():
    css = """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', 'Noto Sans TC', sans-serif;
        background-color: #1E1A1A !important;
        color: #DCD1CC;
    }
    
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at center, #252020 0%, #1E1A1A 100%) !important;
    }
    
    /* Soft Salon Container Panel */
    .cyber-panel {
        background: #2D2525;
        border: 1px solid rgba(226, 164, 153, 0.15);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        position: relative;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
    }
    
    /* KPI Metric styling overrides */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        font-family: 'Outfit', 'Noto Sans TC', sans-serif !important;
        color: #E2A499 !important; /* Rose gold metrics */
    }
    div[data-testid="stMetricLabel"] {
        color: #A39690 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }
    
    /* Soft Salon Card (Netflix Style Hover Preview) */
    .cyber-card {
        background: #2D2525;
        border: 1px solid rgba(226, 164, 153, 0.12);
        border-radius: 12px;
        overflow: hidden;
        position: relative;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        margin-bottom: 15px;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    }
    .cyber-card:hover {
        transform: scale(1.03) translateY(-4px);
        border-color: rgba(226, 164, 153, 0.35);
        box-shadow: 0 12px 24px rgba(226, 164, 153, 0.12);
    }
    
    /* Hover video implementation */
    .cyber-card-img-container {
        position: relative;
        width: 100%;
        aspect-ratio: 16/10;
        overflow: hidden;
        background: #1E1A1A;
        border-bottom: 1px solid rgba(226, 164, 153, 0.1);
    }
    .static-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 1;
        transition: opacity 0.3s ease;
    }
    .hover-video {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }
    .cyber-card:hover .static-img {
        opacity: 0;
    }
    .cyber-card:hover .hover-video {
        opacity: 1;
    }
    
    /* Card details */
    .cyber-card-content {
        padding: 14px;
        font-family: 'Outfit', 'Noto Sans TC', sans-serif;
    }
    .cyber-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #DCD1CC;
        margin-bottom: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .cyber-card-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #A39690;
    }
    .resonance-indicator {
        font-size: 0.8rem;
        color: #E2A499; /* Rose gold highlight */
        font-weight: 600;
    }
    
    /* Sidebar Overrides */
    section[data-testid="stSidebar"] {
        background-color: #2D2525 !important;
        border-right: 1px solid rgba(226, 164, 153, 0.1);
    }
    
    /* Streamlit Dialog Overrides */
    div[role="dialog"] {
        background-color: #2D2525 !important;
        border: 1px solid rgba(226, 164, 153, 0.2) !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4) !important;
        border-radius: 16px !important;
    }
    
    /* Heading style tweaks */
    h1, h2, h3, h4, h5, h6 {
        color: #DCD1CC !important;
        font-family: 'Outfit', 'Noto Sans TC', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Input customization */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: rgba(30, 26, 26, 0.5) !important;
        border: 1px solid rgba(226, 164, 153, 0.15) !important;
        color: #DCD1CC !important;
        font-family: 'Outfit', 'Noto Sans TC', sans-serif !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #E2A499 !important;
        box-shadow: 0 0 0 1px #E2A499 !important;
    }
    
    /* Streamlit standard buttons custom */
    div.stButton > button {
        background: linear-gradient(45deg, #E2A499 0%, #C88E84 100%) !important;
        color: #1E1A1A !important; /* Dark text for contrast */
        font-family: 'Outfit', 'Noto Sans TC', sans-serif !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(226, 164, 153, 0.15) !important;
        transition: all 0.2s ease !important;
        width: 100%;
        margin-top: 5px;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(226, 164, 153, 0.25) !important;
        color: #1E1A1A !important;
    }
    
    /* Primary buttons */
    div.stButton > button[class*="primary"] {
        background: linear-gradient(45deg, #E2A499 0%, #C88E84 100%) !important;
        color: #1E1A1A !important;
    }
    
    /* Progress bar styling */
    div[data-testid="stProgress"] > div > div > div > div {
        background-color: #E2A499 !important;
        box-shadow: 0 0 8px rgba(226, 164, 153, 0.4);
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1E1A1A;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(226, 164, 153, 0.15);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(226, 164, 153, 0.35);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
