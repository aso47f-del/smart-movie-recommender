import streamlit as st
import requests
import random
import time
import json
import os

# 1. Page Configuration
st.set_page_config(
    page_title="Smart Entertainment Hub - Movies, TV & Anime",
    page_icon="🎬",
    layout="wide"
)

# 2. CSS Styling for Smooth Transitions & Modern Clean UI
st.markdown("""
    <style>
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(6px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .block-container, div[data-testid="stVerticalBlock"] > div {
        animation: fadeIn 0.35s ease-in-out;
    }

    div[data-testid="stImage"] img {
        border-radius: 12px;
        transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
    }
    div[data-testid="stImage"] img:hover {
        transform: scale(1.03);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
    }
    .movie-info {
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
        text-align: center;
    }
    .movie-rating { color: #ffb703; }
    .movie-match { color: #2ec4b6; }
    .stApp { background: #0b0b0f; }
    .movie-section-title { font-size: 1.45rem; font-weight: 800; margin: 1.2rem 0 .35rem; border-left: 4px solid #f5c518; padding-left: .65rem; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
    div.stButton > button[kind="secondary"] { background: #19191f; border: 1px solid #35353d; }
    [data-testid="stCaptionContainer"] { color: #b8b8c4; }

    div[data-baseweb="popover"] {
        min-width: 320px !important;
        max-width: min(560px, 90vw) !important;
    }
    div[data-baseweb="popover"] ul[role="listbox"] {
        max-height: 420px !important;
        overflow-y: auto !important;
        padding: 6px !important;
    }
    div[data-baseweb="popover"] li[role="option"] {
        min-height: 46px !important;
        padding: 10px 14px !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 700;
        height: 2.8rem;
        white-space: normal;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Secure API Key Management
try:
    API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    st.error("Please configure TMDB_API_KEY in Streamlit secrets.")
    st.stop()

# Optional persistent storage for hosted deployments (Supabase)
try:
    SUPABASE_URL = str(st.secrets.get("SUPABASE_URL", "")).rstrip("/")
    SUPABASE_SERVICE_ROLE_KEY = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", ""))
except Exception:
    SUPABASE_URL = ""
    SUPABASE_SERVICE_ROLE_KEY = ""

def supabase_storage_enabled():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

def supabase_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

def get_watchlist_filename(email):
    safe_email = "".join([c if c.isalnum() else "_" for c in email])
    return f"watchlist_{safe_email}.json"

def load_user_watchlist(email):
    if supabase_storage_enabled():
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/movie_watchlists",
                params={"user_email": f"eq.{email}", "select": "items", "limit": "1"},
                headers=supabase_headers(), timeout=8,
            )
            response.raise_for_status()
            rows = response.json()
            if rows:
                items = rows[0].get("items", [])
                return items if isinstance(items, list) else []
            return []
        except Exception:
            return []
    filename = get_watchlist_filename(email)
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_user_watchlist(email, watchlist):
    if supabase_storage_enabled():
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/movie_watchlists",
                params={"on_conflict": "user_email"},
                headers={**supabase_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
                json={"user_email": email, "items": watchlist}, timeout=8,
            )
            return True
        except Exception:
            return False
    filename = get_watchlist_filename(email)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def normalize_watchlist_item(item):
    normalized = dict(item)
    normalized.setdefault("status", "Want to Watch")
    normalized.setdefault("personal_rating", 0)
    normalized.setdefault("note", "")
    normalized.setdefault("media_type", "movie")
    return normalized

# Authentication check
try:
    is_logged_in = bool(st.user.is_logged_in)
except Exception:
    is_logged_in = False

if is_logged_in:
    user_email = st.user.get("email", "user@gmail.com")
    user_name = st.user.get("name", "User")
    watchlist_owner = user_email
else:
    user_email = ""
    user_name = "Guest"
    watchlist_owner = "guest_session"

NO_IMAGE_URL = "https://via.placeholder.com/500x750?text=No+Poster+Available"

# --- Helper Formatting Function for TMDB Items ---
def format_tmdb_items(items, media_type="movie"):
    formatted = []
    for item in items or []:
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
        date_key = "release_date" if media_type == "movie" else "first_air_date"
        title_key = "title" if media_type == "movie" else "name"
        release_date = item.get(date_key) or "N/A"
        rating = item.get("vote_average", 0.0) or 0.0
        
        # If anime section, filter or prioritize Japanese animation (genre 16)
        genre_ids = item.get("genre_ids", [])
        orig_lang = item.get("original_language", "")
        if media_type == "anime":
            if 16 not in genre_ids and orig_lang != "ja":
                continue # Skip non-anime items if strictly filtering

        formatted.append({
            "movie_id": item.get("id"),
            "id": item.get("id"),
            "media_type": "movie" if media_type == "movie" else "tv",
            "title": item.get(title_key) or "Untitled",
            "poster": poster_url,
            "rating": round(rating, 1),
            "year": release_date[:4] if release_date != "N/A" else "N/A",
            "match": min(99, int(item.get("popularity", 50)) % 15 + 80),
            "overview": item.get("overview", "")
        })
    return formatted

# --- API Functions for Movies, TV & Anime ---

@st.cache_data(show_spinner=False, ttl=86400)
def search_tmdb(query, media_type="movie"):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/search/{endpoint}?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if media_type == "anime":
                # Filter for Japanese animation or anime keywords
                results = [r for r in results if 16 in r.get("genre_ids", []) or r.get("original_language") == "ja"]
            return format_tmdb_items(results, "movie" if media_type == "movie" else "tv")
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_home_media(section, media_type="movie", page=1):
    endpoint = "movie" if media_type == "movie" else "tv"
    if section == "Trending":
        url = f"https://api.themoviedb.org/3/trending/{endpoint}/week?api_key={API_KEY}&language=en-US&page={page}"
    elif section == "Top Rated":
        url = f"https://api.themoviedb.org/3/{endpoint}/top_rated?api_key={API_KEY}&language=en-US&page={page}"
    else:
        genre_ids = {
            "Action": 28 if media_type == "movie" else 10759,
            "Horror": 27,
            "Animation": 16,
            "Drama": 18,
            "Comedy": 35,
            "Adventure": 12 if media_type == "movie" else 10759,
            "Sci-Fi": 878 if media_type == "movie" else 10765
        }
        genre_id = genre_ids.get(section, 16 if media_type == "anime" else 28)
        
        if media_type == "anime":
            url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16&with_original_language=ja&sort_by=popularity.desc&page={page}"
        else:
            url = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&page={page}"
            
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return format_tmdb_items(results, "movie" if media_type == "movie" else "tv")
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=604800)
def fetch_modal_data(item_id, media_type="movie"):
    endpoint = "movie" if media_type == "movie" else "tv"
    info_url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}?api_key={API_KEY}&language=en-US"
    videos_url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/videos?api_key={API_KEY}&language=en-US"
    credits_url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/credits?api_key={API_KEY}&language=en-US"
    
    overview, runtime, imdb_id, youtube_key, director, cast = "No overview available.", "N/A", None, None, "N/A", []
    try:
        res_info = requests.get(info_url, timeout=5)
        if res_info.status_code == 200:
            data = res_info.json()
            overview = data.get("overview", "No overview available.")
            if media_type == "movie":
                runtime = f"{data.get('runtime', 0)} mins"
            else:
                seasons = data.get('number_of_seasons', 0)
                episodes = data.get('number_of_episodes', 0)
                runtime = f"{seasons} Seasons, {episodes} Episodes"
            imdb_id = data.get("imdb_id")
            
        res_vid = requests.get(videos_url, timeout=5)
        if res_vid.status_code == 200:
            for vid in res_vid.json().get("results", []):
                if vid.get("site") == "YouTube" and vid.get("type") in ["Trailer", "Teaser"]:
                    youtube_key = vid.get("key")
                    break
                    
        res_credits = requests.get(credits_url, timeout=5)
        if res_credits.status_code == 200:
            c_data = res_credits.json()
            crew_list = c_data.get("crew", [])
            for person in crew_list:
                if person.get("job") == "Director" or person.get("job") == "Series Creator":
                    director = person.get("name")
                    break
            if director == "N/A" and crew_list:
                director = crew_list[0].get("name", "N/A")
            cast = c_data.get("cast", [])[:4]
    except Exception:
        pass
    return overview, runtime, imdb_id, youtube_key, director, cast

@st.cache_data(show_spinner=False, ttl=86400)
def get_watch_providers(item_id, media_type="movie"):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/watch/providers?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get("results", {})
            for country in ['EG', 'US', 'GB']:
                if country in data and 'flatrate' in data[country]:
                    return data[country]['flatrate']
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_recommendations(item_id, media_type="movie"):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/recommendations?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            return format_tmdb_items(results, media_type)
    except Exception:
        pass
    return []

# --- Details Modal ---
@st.dialog("🎬 Details, Cast & Trailer", width="large")
def show_details_modal(item, prefix="modal"):
    m_type = item.get("media_type", "movie")
    overview, runtime, imdb_id, youtube_key, director, cast = fetch_modal_data(item['movie_id'], m_type)
    providers = get_watch_providers(item['movie_id'], m_type)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(item['poster'], use_container_width=True)
        st.markdown(f"**Year / Air Date:** {item['year']}")
        st.markdown(f"**Duration:** {runtime}")
        st.markdown(f"**Rating:** ⭐ {item['rating']}/10")
        
        if "watchlist" not in st.session_state:
            st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
        
        is_in_watchlist = any(m['movie_id'] == item['movie_id'] for m in st.session_state.watchlist)
        if not is_in_watchlist:
            if st.button("❤️ Add to Watchlist", key=f"{prefix}_add_{item['movie_id']}"):
                watch_item = normalize_watchlist_item(item)
                st.session_state.watchlist.append(watch_item)
                if is_logged_in:
                    save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                    st.toast("Added to your Watchlist! ❤️", icon="✅")
                st.rerun()
        else:
            if st.button("❌ Remove from Watchlist", key=f"{prefix}_rem_{item['movie_id']}"):
                st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                if is_logged_in:
                    save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                st.toast("Removed from watchlist.", icon="🗑️")
                st.rerun()
        
    with col2:
        st.subheader(f"{item['title']} ({item['year']})")
        st.markdown(f"🎬 **Creator / Director:** {director}")
        st.markdown("**Overview:**")
        st.write(overview)
        
        if cast:
            st.markdown("**👥 Top Cast:**")
            cast_cols = st.columns(len(cast))
            for i, actor in enumerate(cast):
                with cast_cols[i]:
                    profile_path = actor.get("profile_path")
                    img_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else NO_IMAGE_URL
                    st.image(img_url, use_container_width=True)
                    st.caption(actor.get('name'))
        
        st.markdown("**📺 Where to Watch:**")
        if providers:
            prov_cols = st.columns(min(len(providers), 4))
            for i, prov in enumerate(providers[:4]):
                with prov_cols[i]:
                    logo_path = prov.get("logo_path")
                    if logo_path:
                        st.image(f"https://image.tmdb.org/t/p/w92{logo_path}", width=45)
                    st.caption(prov.get("provider_name"))
        else:
            st.info("No online streaming providers available right now.")
        
        if youtube_key:
            st.markdown("**Official Trailer:**")
            st.video(f"https://www.youtube.com/watch?v={youtube_key}")
        else:
            st.info("No trailer video available.")

# --- Top Navigation: 3 Main Categories + Watchlist ---
if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "🎬 أفلام (Movies)"

top_col1, top_col2, top_col3, top_col4 = st.columns([1, 1, 1, 1], vertical_alignment="center")
with top_col1:
    if st.button("🎬 أفلام (Movies)", use_container_width=True, type="primary" if st.session_state.active_main_tab == "🎬 أفلام (Movies)" else "secondary"):
        st.session_state.active_main_tab = "🎬 أفلام (Movies)"
        st.rerun()
with top_col2:
    if st.button("📺 مسلسلات (TV Shows)", use_container_width=True, type="primary" if st.session_state.active_main_tab == "📺 مسلسلات (TV Shows)" else "secondary"):
        st.session_state.active_main_tab = "📺 مسلسلات (TV Shows)"
        st.rerun()
with top_col3:
    if st.button("🍙 أنمي (Anime)", use_container_width=True, type="primary" if st.session_state.active_main_tab == "🍙 أنمي (Anime)" else "secondary"):
        st.session_state.active_main_tab = "🍙 أنمي (Anime)"
        st.rerun()
with top_col4:
    if st.button("❤️ قائمة المشاهدة (Watchlist)", use_container_width=True, type="primary" if st.session_state.active_main_tab == "❤️ Watchlist" else "secondary"):
        st.session_state.active_main_tab = "❤️ Watchlist"
        st.rerun()

st.markdown("---")

# Determine current media type based on active tab
active_tab = st.session_state.active_main_tab

if active_tab == "❤️ Watchlist":
    st.title("❤️ قائمة المشاهدة الخاصة بك (My Watchlist)")
    st.caption("تابع الأفلام والمسلسلات والأنمي التي أضفتها لقائمتك.")
    if not st.session_state.get("watchlist"):
        st.info("قائمتك فارغة حالياً. تصفح الأقسام المختلفة وأضف ما يعجبك!")
    else:
        watchlist_items = [normalize_watchlist_item(m) for m in st.session_state.watchlist]
        COLS_PER_ROW = 5
        for row_start in range(0, len(watchlist_items), COLS_PER_ROW):
            row_items = watchlist_items[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW, gap="medium")
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10 · {item["year"]}</div>', unsafe_allow_html=True)
                        if st.button(f"{item['title']}", key=f"btn_watch_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                            show_details_modal(item, prefix=f"watch_{row_start + idx}")
                        if st.button("❌ إزالة", key=f"rem_w_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                            st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                            if is_logged_in:
                                save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                            st.rerun()

else:
    # Set media type and labels
    if active_tab == "🎬 أفلام (Movies)":
        media_type = "movie"
        section_title = "🎬 قسم الأفلام"
    elif active_tab == "📺 مسلسلات (TV Shows)":
        media_type = "tv"
        section_title = "📺 قسم المسلسلات"
    else:
        media_type = "anime"
        section_title = "🍙 قسم الأنمي"

    st.title(section_title)
    
    # Each section has its own Search & Recommendations Bar
    with st.form(key=f"search_form_{media_type}"):
        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            search_query = st.text_input(f"بحث في {active_tab}:", placeholder="اكتب اسم العرض للبحث أو للحصول على ترشيحات شبيهة...", label_visibility="collapsed")
        with col_s2:
            search_submitted = st.form_submit_button("🔍 بحث وترشيحات", use_container_width=True)

    if search_submitted and search_query.strip():
        st.subheader(f"نتائج البحث والترشيحات لـ: {search_query}")
        results = search_tmdb(search_query.strip(), media_type)
        if not results:
            st.warning("لم يتم العثور على نتائج مطابقة.")
        else:
            # Show top match and its recommendations
            top_item = results[0]
            st.markdown(f"### النتيجة الأبرز: {top_item['title']}")
            
            c1, c2 = st.columns([1, 4])
            with c1:
                st.image(top_item['poster'], use_container_width=True)
            with c2:
                st.write(top_item['overview'])
                if st.button("🎬 عرض التفاصيل والترشيحات", key=f"top_res_{top_item['movie_id']}"):
                    show_details_modal(top_item, prefix="top_res")
            
            st.markdown("---")
            st.subheader("🍿 ترشيحات مشابهة:")
            recs = get_recommendations(top_item['movie_id'], media_type)
            if recs:
                rec_cols = st.columns(min(len(recs), 5))
                for i, rec in enumerate(recs[:5]):
                    with rec_cols[i]:
                        st.image(rec['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-info">⭐ {rec["rating"]}/10</div>', unsafe_allow_html=True)
                        if st.button(rec['title'], key=f"rec_click_{rec['movie_id']}_{i}", use_container_width=True):
                            show_details_modal(rec, prefix=f"rec_{i}")
            else:
                st.info("لا توجد ترشيحات متاحة حالياً لهذا العنوان.")

    st.markdown("---")
    
    # Home Carousels / Rows for the active category
    def render_row(section_key, title):
        items = get_home_media(section_key, media_type)
        if items:
            st.markdown(f'<div class="movie-section-title">{title}</div>', unsafe_allow_html=True)
            cols = st.columns(5)
            for i, item in enumerate(items[:5]):
                with cols[i]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10 · {item["year"]}</div>', unsafe_allow_html=True)
                    if st.button(item['title'], key=f"row_{media_type}_{section_key}_{item['movie_id']}_{i}", use_container_width=True):
                        show_details_modal(item, prefix=f"{section_key}_{i}")

    render_row("Trending", "🔥 الأكثر رواجاً هذا الأسبوع")
    render_row("Top Rated", "⭐ الأعلى تقييماً")
    render_row("Animation" if media_type != "anime" else "Action", "💥 الأبرز في التصنيف")
