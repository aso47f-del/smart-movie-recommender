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

# Optional Supabase storage
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

ALL_GENRES = [
    "All", "Action", "Adventure", "Animation", "Comedy", "Crime", 
    "Documentary", "Drama", "Family", "Fantasy", "History", 
    "Horror", "Music", "Mystery", "Romance", "Science Fiction", 
    "Thriller", "War", "Western"
]

POPULAR_COLLECTIONS = {
    "John Wick Collection": 404366,
    "The Dark Knight Trilogy": 263,
    "Harry Potter Collection": 1241,
    "The Lord of the Rings Collection": 119,
    "Star Wars Collection": 10,
    "Marvel Avengers Universe": 86311,
    "The Godfather Collection": 230,
}

MOOD_OPTIONS = {
    "Adrenaline & Adventure 🏃‍♂️": {"genres": "28,12", "sort": "popularity.desc"},
    "Mystery & Psychological 🧠": {"genres": "9648,53", "sort": "vote_average.desc"},
    "Scared / Horror 👻": {"genres": "27", "sort": "popularity.desc"},
    "Feel-good & Comedy 😄": {"genres": "35,10751", "sort": "popularity.desc"},
    "Romance & Drama 💖": {"genres": "10749,18", "sort": "vote_average.desc"},
    "Sci-Fi & Fantasy 🚀": {"genres": "878,14", "sort": "popularity.desc"},
    "Animation & Anime 🍿": {"genres": "16", "sort": "vote_average.desc"}
}

# --- Formatting Helper ---
def format_tmdb_items(items, media_type="movie"):
    formatted = []
    for item in items or []:
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
        date_key = "release_date" if media_type == "movie" else "first_air_date"
        title_key = "title" if media_type == "movie" else "name"
        release_date = item.get(date_key) or "N/A"
        rating = item.get("vote_average", 0.0) or 0.0
        
        if media_type == "anime":
            genre_ids = item.get("genre_ids", [])
            orig_lang = item.get("original_language", "")
            if 16 not in genre_ids and orig_lang != "ja":
                continue

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

# --- API Functions ---
@st.cache_data(show_spinner=False, ttl=86400)
def search_tmdb(query, media_type="movie"):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/search/{endpoint}?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if media_type == "anime":
                results = [r for r in results if 16 in r.get("genre_ids", []) or r.get("original_language") == "ja"]
            return format_tmdb_items(results, media_type)
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
        genre_ids = {"Action": 28 if media_type=="movie" else 10759, "Horror": 27, "Animation": 16, "Drama": 18, "Comedy": 35, "Adventure": 12 if media_type=="movie" else 10759}
        genre_id = genre_ids.get(section, 16 if media_type=="anime" else 28)
        if media_type == "anime":
            url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16&with_original_language=ja&sort_by=popularity.desc&page={page}"
        else:
            url = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&page={page}"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return format_tmdb_items(response.json().get("results", []), media_type)
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def discover_by_mood(genre_ids, sort_by, media_type="movie", page=1):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={API_KEY}&with_genres={genre_ids}&sort_by={sort_by}&page={page}&language=en-US&vote_count.gte=50"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            total_pages = min(data.get("total_pages", 1), 10)
            return format_tmdb_items(results, media_type), total_pages
    except Exception:
        pass
    return [], 1

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
            for person in c_data.get("crew", []):
                if person.get("job") in ["Director", "Series Creator"]:
                    director = person.get("name")
                    break
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
            return format_tmdb_items(res.json().get("results", []), media_type)
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def search_person_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/person?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            return sorted(results, key=lambda x: x.get("popularity", 0), reverse=True)
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_person_details(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

@st.cache_data(show_spinner=False, ttl=604800)
def get_person_filmography(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/combined_credits?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            all_dict = {}
            for m in data.get("cast", []) + data.get("crew", []):
                m_id = m.get("id")
                if m_id and m_id not in all_dict:
                    all_dict[m_id] = m
            sorted_items = sorted(list(all_dict.values()), key=lambda x: x.get("popularity", 0), reverse=True)
            formatted = []
            for item in sorted_items:
                m_type = "movie" if item.get("media_type") == "movie" or "title" in item else "tv"
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                date_key = "release_date" if m_type == "movie" else "first_air_date"
                title_key = "title" if m_type == "movie" else "name"
                formatted.append({
                    'movie_id': item.get("id"),
                    'id': item.get("id"),
                    'media_type': m_type,
                    'title': item.get(title_key, "Untitled"),
                    'poster': poster_url,
                    'rating': round(item.get("vote_average", 0.0), 1),
                    'year': (item.get(date_key) or "N/A")[:4]
                })
            return formatted
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def search_collection_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/collection?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=604800)
def get_collection_details(collection_id):
    url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            parts = sorted(data.get("parts", []), key=lambda x: x.get("release_date", "9999") or "9999")
            formatted_parts = []
            for item in parts:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                formatted_parts.append({
                    'movie_id': item.get("id"),
                    'id': item.get("id"),
                    'media_type': 'movie',
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': round(item.get("vote_average", 0.0), 1),
                    'year': (item.get("release_date") or "N/A")[:4],
                    'overview': item.get("overview", "")
                })
            poster_path = data.get("poster_path")
            return {
                'id': data.get("id"),
                'name': data.get("name"),
                'overview': data.get("overview", ""),
                'poster': f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL,
                'parts': formatted_parts
            }
    except Exception:
        pass
    return None

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

# --- Navigation Setup ---
if "main_media_type" not in st.session_state:
    st.session_state.main_media_type = "movie"

if "main_nav_tab" not in st.session_state:
    st.session_state.main_nav_tab = "🏠 Home"

# Top Media Type Selector, Menu, and Account Controls
nav_m1, nav_m2, nav_m3, nav_menu_col, nav_acc = st.columns([1, 1, 1, 1.8, 1.1], vertical_alignment="center")
with nav_m1:
    if st.button("🎬 Movies", use_container_width=True, type="primary" if st.session_state.main_media_type == "movie" else "secondary"):
        st.session_state.main_media_type = "movie"
        st.rerun()
with nav_m2:
    if st.button("📺 TV Shows", use_container_width=True, type="primary" if st.session_state.main_media_type == "tv" else "secondary"):
        st.session_state.main_media_type = "tv"
        st.rerun()
with nav_m3:
    if st.button("🍙 Anime", use_container_width=True, type="primary" if st.session_state.main_media_type == "anime" else "secondary"):
        st.session_state.main_media_type = "anime"
        st.rerun()
with nav_menu_col:
    menu_options = {
        "Home": "🏠 Home",
        "Recommendations": "🍿 Discover & Recommendations",
        "Mood Finder": "🎲 Mood Finder",
        "Franchises": "🎞️ Franchises & Collections",
        "Actors": "🎭 Actors & Directors",
        "Watchlist": "❤️ My Watchlist"
    }
    chosen_menu = st.selectbox("Navigation Menu", list(menu_options.keys()), format_func=lambda x: menu_options[x], key="top_menu_selector", label_visibility="collapsed")
    st.session_state.main_nav_tab = menu_options[chosen_menu]
with nav_acc:
    if is_logged_in:
        st.caption(f"👤 {user_name}")
        if st.button("Sign out", key="top_signout", use_container_width=True):
            st.logout()
    else:
        if st.button("Sign in", key="top_signin", use_container_width=True):
            try:
                st.login("google")
            except Exception:
                st.error("Google sign-in is not configured yet. You can browse as guest.")

st.markdown("---")

current_media = st.session_state.main_media_type
active_tab = st.session_state.main_nav_tab

# --- TAB 1: Home ---
if active_tab == "🏠 Home":
    media_name = "Movies" if current_media == "movie" else ("TV Shows" if current_media == "tv" else "Anime")
    st.title(f"🏠 Discover {media_name}")
    st.caption(f"Trending picks, top-rated {media_name.lower()}, and genre favorites.")
    
    def render_row(section_key, title):
        items = get_home_media(section_key, current_media)
        if items:
            st.markdown(f'<div class="movie-section-title">{title}</div>', unsafe_allow_html=True)
            cols = st.columns(5)
            for i, item in enumerate(items[:5]):
                with cols[i]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10 · {item["year"]}</div>', unsafe_allow_html=True)
                    if st.button(item['title'], key=f"row_{current_media}_{section_key}_{item['movie_id']}_{i}", use_container_width=True):
                        show_details_modal(item, prefix=f"{section_key}_{i}")

    render_row("Trending", "🔥 Trending This Week")
    render_row("Top Rated", "⭐ Top Rated")
    render_row("Action", "💥 Action & Adventure")
    render_row("Animation", "🍿 Animation & Cartoons")
    render_row("Horror", "👻 Horror / Suspense")
    render_row("Drama", "🎭 Drama")

# --- TAB 2: Discover & Recommendations ---
elif active_tab == "🍿 Discover & Recommendations":
    st.title("🍿 Recommendations & Search")
    st.caption("Search any title or get tailored recommendations instantly.")
    
    query = st.text_input(f"Search {current_media} title:", placeholder="Type a title...")
    if query:
        results = search_tmdb(query, current_media)
        if results:
            sel_title = st.selectbox("Select from results:", [f"{r['title']} ({r['year']})" for r in results])
            selected_item = next((r for r in results if f"{r['title']} ({r['year']})" == sel_title), results[0])
            
            c1, c2 = st.columns([1, 3])
            with c1:
                st.image(selected_item['poster'], use_container_width=True)
            with c2:
                st.subheader(selected_item['title'])
                st.write(selected_item['overview'])
                if st.button("View Full Details & Trailer", key="rec_modal_btn"):
                    show_details_modal(selected_item, prefix="rec_main")
            
            st.markdown("---")
            st.subheader("🍿 Similar Recommendations:")
            recs = get_recommendations(selected_item['movie_id'], current_media)
            if recs:
                cols = st.columns(5)
                for i, rec in enumerate(recs[:5]):
                    with cols[i]:
                        st.image(rec['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-info">⭐ {rec["rating"]}/10</div>', unsafe_allow_html=True)
                        if st.button(rec['title'], key=f"rec_item_{rec['movie_id']}_{i}", use_container_width=True):
                            show_details_modal(rec, prefix=f"recs_{i}")
        else:
            st.info("No results found.")

# --- TAB 3: Mood Finder ---
elif active_tab == "🎲 Mood Finder":
    st.title("🎲 Mood Finder")
    st.caption("Choose what you feel like watching right now.")
    selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()))
    mood_data = MOOD_OPTIONS[selected_mood]
    
    mood_items, total_pages = discover_by_mood(mood_data["genres"], mood_data["sort"], current_media)
    if mood_items:
        cols = st.columns(5)
        for i, item in enumerate(mood_items[:10]):
            with cols[i % 5]:
                st.image(item['poster'], use_container_width=True)
                st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10</div>', unsafe_allow_html=True)
                if st.button(item['title'], key=f"mood_item_{item['movie_id']}_{i}", use_container_width=True):
                    show_details_modal(item, prefix=f"mood_{i}")
    else:
        st.info("No items found for this mood.")

# --- TAB 4: Franchises & Collections ---
elif active_tab == "🎞️ Franchises & Collections":
    st.title("🎞️ Franchises & Collections")
    st.caption("Browse cinematic universes and collections in order.")
    search_mode = st.radio("Mode:", ["Popular Franchises ⭐", "Search Any Franchise 🔍"], horizontal=True)
    
    coll_id = None
    if search_mode == "Popular Franchises ⭐":
        preset = st.selectbox("Select Franchise:", list(POPULAR_COLLECTIONS.keys()))
        coll_id = POPULAR_COLLECTIONS.get(preset)
    else:
        q = st.text_input("Search Collection:")
        if q:
            res = search_collection_tmdb(q)
            if res:
                opts = {c.get("name"): c.get("id") for c in res}
                chosen_c = st.selectbox("Select:", list(opts.keys()))
                coll_id = opts.get(chosen_c)
                
    if coll_id:
        collection = get_collection_details(coll_id)
        if collection:
            st.markdown(f"## {collection['name']}")
            st.write(collection['overview'])
            st.markdown("### Chronological Parts:")
            cols = st.columns(5)
            for i, part in enumerate(collection['parts']):
                with cols[i % 5]:
                    st.image(part['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info">⭐ {part["rating"]}/10</div>', unsafe_allow_html=True)
                    if st.button(part['title'], key=f"coll_part_{part['movie_id']}_{i}", use_container_width=True):
                        show_details_modal(part, prefix=f"coll_{i}")

# --- TAB 5: Actors & Directors ---
elif active_tab == "🎭 Actors & Directors":
    st.title("🎭 Actors & Directors")
    st.caption("Search performers or creators and explore their complete filmography.")
    p_query = st.text_input("Search Person:")
    if p_query:
        p_results = search_person_tmdb(p_query)
        if p_results:
            p_opts = {f"{p.get('name')} ({p.get('known_for_department', 'Artist')})": p for p in p_results}
            chosen_p = st.selectbox("Select Person:", list(p_opts.keys()))
            person = p_opts.get(chosen_p)
            
            if person:
                details = get_person_details(person.get("id"))
                c1, c2 = st.columns([1, 3])
                with c1:
                    profile_path = details.get("profile_path") or person.get("profile_path")
                    st.image(f"https://image.tmdb.org/t/p/w342{profile_path}" if profile_path else NO_IMAGE_URL, use_container_width=True)
                with c2:
                    st.subheader(details.get("name"))
                    st.write(details.get("biography", "No biography available."))
                
                st.markdown("### Filmography:")
                filmography = get_person_filmography(person.get("id"))
                if filmography:
                    cols = st.columns(5)
                    for i, item in enumerate(filmography[:15]):
                        with cols[i % 5]:
                            st.image(item['poster'], use_container_width=True)
                            st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10</div>', unsafe_allow_html=True)
                            if st.button(item['title'], key=f"pers_work_{item['movie_id']}_{i}", use_container_width=True):
                                show_details_modal(item, prefix=f"pers_{i}")

# --- TAB 6: Watchlist ---
elif active_tab == "❤️ My Watchlist":
    st.title(f"❤️ {user_name}'s Watchlist")
    st.caption("Your saved movies, TV shows, and anime.")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
        
    if not st.session_state.watchlist:
        st.info("Your Watchlist is empty.")
    else:
        cols = st.columns(5)
        for i, item in enumerate(st.session_state.watchlist):
            with cols[i % 5]:
                with st.container(border=True):
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info">⭐ {item["rating"]}/10</div>', unsafe_allow_html=True)
                    if st.button(item['title'], key=f"wl_item_{item['movie_id']}_{i}", use_container_width=True):
                        show_details_modal(item, prefix=f"wl_{i}")
                    if st.button("❌ Remove", key=f"wl_rem_{item['movie_id']}_{i}", use_container_width=True):
                        st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                        if is_logged_in:
                            save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                        st.rerun()
