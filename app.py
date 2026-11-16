import streamlit as st
import requests
import random
import time
import json
import os

# 1. Page Configuration
st.set_page_config(
    page_title="Smart Live Movie, TV & Anime Hub",
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
    .media-info {
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
        text-align: center;
    }
    .media-rating { color: #ffb703; }
    .media-match { color: #2ec4b6; }
    .stApp { background: #0b0b0f; }
    .media-section-title { font-size: 1.45rem; font-weight: 800; margin: 1.2rem 0 .35rem; }
    .home-subtitle { color: #b8b8c4; margin-top: -.5rem; }
    .media-section-title { border-left: 4px solid #f5c518; padding-left: .65rem; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
    .top-brand { font-size: 1.35rem; font-weight: 900; letter-spacing: -.4px; }
    .top-brand span { color: #f5c518; }
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
        line-height: 1.45 !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="popover"] li[role="option"] * {
        font-size: inherit !important;
        line-height: inherit !important;
    }
    div[data-baseweb="select"] > div {
        min-height: 44px;
    }
    .watchlist-card { min-height: 100%; }
    .watchlist-card-title { min-height: 2.7rem; font-weight: 750; text-align: center; }
    @media (max-width: 760px) {
        div[data-baseweb="popover"] { min-width: min(290px, 88vw) !important; }
        div[data-baseweb="popover"] li[role="option"] { min-height: 44px !important; }

        .block-container { padding-left: .7rem; padding-right: .7rem; }
        .media-section-title { font-size: 1.1rem; }
        div[data-testid="stHorizontalBlock"] { gap: .35rem; }
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
        except Exception as exc:
            st.warning(f"Could not load your cloud Watchlist right now: {exc}")
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
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/movie_watchlists",
                params={"on_conflict": "user_email"},
                headers={**supabase_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
                json={"user_email": email, "items": watchlist}, timeout=8,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            st.warning(f"Could not save your cloud Watchlist right now: {exc}")
            return False
    filename = get_watchlist_filename(email)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        st.warning("Could not save the Watchlist locally.")
        return False

def normalize_watchlist_item(item):
    normalized = dict(item)
    normalized.setdefault("status", "Want to Watch")
    normalized.setdefault("personal_rating", 0)
    normalized.setdefault("note", "")
    normalized.setdefault("media_type", "movie")
    return normalized

# 4. Optional Google Authentication
try:
    is_logged_in = bool(st.user.is_logged_in)
except Exception:
    is_logged_in = False

if is_logged_in:
    user_email = st.user.get("email", "user@gmail.com")
    user_name = st.user.get("name", "Media Fan")
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
    "TV Movie", "Thriller", "War", "Western"
]

POPULAR_COLLECTIONS = {
    "John Wick Collection": 404366,
    "The Dark Knight Trilogy": 263,
    "Harry Potter Collection": 1241,
    "The Lord of the Rings Collection": 119,
    "Star Wars Collection": 10,
    "Jurassic Park Collection": 328,
    "Fast & Furious Collection": 9485,
    "Pirates of the Caribbean Collection": 295,
    "X-Men Collection": 748,
    "Transformers Collection": 8650,
    "Mission: Impossible Collection": 87096,
    "The Avengers Collection": 86311,
    "The Godfather Collection": 230,
    "Toy Story Collection": 10194
}

MOOD_OPTIONS = {
    "Adrenaline & Adventure 🏃‍♂️": {"genres": "28,12", "sort": "popularity.desc"},
    "Mystery & Psychological 🧠": {"genres": "9648,53", "sort": "vote_average.desc"},
    "Scared / Horror 👻": {"genres": "27", "sort": "popularity.desc"},
    "Feel-good & Comedy 😄": {"genres": "35,10751", "sort": "popularity.desc"},
    "Romance & Drama 💖": {"genres": "10749,18", "sort": "vote_average.desc"},
    "Sci-Fi & Fantasy 🚀": {"genres": "878,14", "sort": "popularity.desc"},
    "Animation & Family 🍿": {"genres": "16,10751", "sort": "vote_average.desc"}
}

# --- API Functions for Movies, TV Shows & Anime ---

@st.cache_data(show_spinner=False, ttl=86400)
def search_media_tmdb(query, media_type="movie"):
    if media_type == "Anime":
        endpoint = "search/tv"
    elif media_type == "TV Shows":
        endpoint = "search/tv"
    elif media_type == "Movies":
        endpoint = "search/movie"
    else:
        endpoint = "search/multi"
        
    url = f"https://api.themoviedb.org/3/{endpoint}?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            formatted = []
            for r in results:
                m_t = r.get("media_type")
                if not m_t:
                    m_t = "movie" if endpoint == "search/movie" else "tv"
                if m_t in ["movie", "tv"]:
                    r["media_type"] = m_t
                    formatted.append(r)
            return formatted
    except Exception as e:
        st.toast(f"⚠️ Connection error during search: {e}", icon="🚨")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def search_collection_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/collection?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception:
        st.toast("⚠️ Error searching collections.", icon="⚠️")
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
        st.toast("⚠️ Error searching persons.", icon="⚠️")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_person_details(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        st.toast("⚠️ Unable to load this person's biography right now.", icon="⚠️")
    return {}

@st.cache_data(show_spinner=False, ttl=604800)
def get_person_filmography(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/combined_credits?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            all_media_dict = {}
            for m in data.get("cast", []) + data.get("crew", []):
                m_id = m.get("id")
                m_type = m.get("media_type", "movie")
                unique_key = f"{m_type}_{m_id}"
                
                # Filter out talk shows, news, and reality TV genres or TV show types if desired
                # TMDB genre ID 10767 is Talk, 10763 is News, 10764 is Reality
                genre_ids = m.get("genre_ids", [])
                if 10767 in genre_ids or 10763 in genre_ids or 10764 in genre_ids:
                    continue
                    
                if m_id and unique_key not in all_media_dict:
                    m["media_type"] = m_type if m_type in ["movie", "tv"] else "movie"
                    all_media_dict[unique_key] = m
                    
            sorted_media = sorted(list(all_media_dict.values()), key=lambda x: x.get("popularity", 0), reverse=True)
            formatted_media = []
            for item in sorted_media:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                title = item.get("title") or item.get("name") or "Untitled"
                date_str = item.get("release_date") or item.get("first_air_date") or "N/A"
                formatted_media.append({
                    'movie_id': item.get("id"),
                    'title': title,
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': date_str[:4],
                    'media_type': item.get("media_type", "movie"),
                    'popularity': item.get("popularity", 0)
                })
            return formatted_media
    except Exception:
        st.toast("⚠️ Error fetching filmography.", icon="⚠️")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def discover_media_by_mood(genre_ids, sort_by, media_type="movie", page=1):
    endpoint = "discover/movie" if media_type == "movie" else "discover/tv"
    url = f"https://api.themoviedb.org/3/{endpoint}?api_key={API_KEY}&with_genres={genre_ids}&sort_by={sort_by}&page={page}&language=en-US&vote_count.gte=30&vote_average.gte=5.0"
    if media_type == "anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16,{genre_ids}&with_original_language=ja&sort_by={sort_by}&page={page}&language=en-US&vote_count.gte=10"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            total_pages = min(data.get("total_pages", 1), 10)
            media_list = []
            for item in results:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                title = item.get("title") or item.get("name") or "Untitled"
                date_str = item.get("release_date") or item.get("first_air_date") or "N/A"
                m_type = "movie" if media_type == "movie" else "tv"
                media_list.append({
                    'movie_id': item.get("id"),
                    'title': title,
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': date_str[:4],
                    'match': int(item.get("popularity", 50)) % 15 + 80,
                    'media_type': m_type
                })
            return media_list, total_pages
    except Exception:
        st.toast("⚠️ Error filtering by mood.", icon="⚠️")
    return [], 1

@st.cache_data(show_spinner=False, ttl=604800)
def get_collection_details(collection_id):
    url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            parts_sorted = sorted(data.get("parts", []), key=lambda x: x.get("release_date", "9999") or "9999")
            formatted_parts = []
            for item in parts_sorted:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                formatted_parts.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': (item.get("release_date") or "N/A")[:4],
                    'overview': item.get("overview", ""),
                    'media_type': 'movie'
                })
            poster_path = data.get("poster_path")
            coll_poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
            return {
                'id': data.get("id"),
                'name': data.get("name"),
                'overview': data.get("overview", ""),
                'poster': coll_poster,
                'parts': formatted_parts
            }
    except Exception:
        st.toast("⚠️ Error fetching collection.", icon="⚠️")
    return None

@st.cache_data(show_spinner=False, ttl=604800)
def fetch_media_modal_data(media_id, media_type="movie"):
    info_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={API_KEY}&language=en-US"
    videos_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos?api_key={API_KEY}&language=en-US"
    credits_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/credits?api_key={API_KEY}&language=en-US"
    
    overview, runtime, imdb_id, youtube_key, creator_director, cast = "No overview available.", "N/A", None, None, "N/A", []
    try:
        res_info = requests.get(info_url, timeout=5)
        if res_info.status_code == 200:
            data = res_info.json()
            overview = data.get("overview", "No overview available.")
            if media_type == "movie":
                runtime = f"{data.get('runtime', 0)} mins"
            else:
                seasons_count = data.get("number_of_seasons", 1)
                eps_count = data.get("number_of_episodes", 0)
                runtime = f"{seasons_count} Season(s) ({eps_count} Eps)"
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
            if media_type == "movie":
                for person in c_data.get("crew", []):
                    if person.get("job") == "Director":
                        creator_director = person.get("name")
                        break
            else:
                creators = c_data.get("created_by", [])
                if creators:
                    creator_director = ", ".join([c.get("name") for c in creators])
                else:
                    creator_director = "N/A"
            cast = c_data.get("cast", [])[:4]
    except Exception:
        st.toast("⚠️ Error loading modal content.", icon="⚠️")
    return overview, runtime, imdb_id, youtube_key, creator_director, cast

@st.cache_data(show_spinner=False, ttl=86400)
def get_media_watch_providers(media_id, media_type="movie"):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get("results", {})
            for country in ['EG', 'GB', 'FR', 'US']:
                if country in data and 'flatrate' in data[country]:
                    return data[country]['flatrate']
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=604800)
def get_media_details(media_id, media_type="movie"):
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            poster_path = data.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
            raw_rating = data.get("vote_average", 0.0)
            title = data.get("title") or data.get("name") or "Untitled"
            date_str = data.get("release_date") or data.get("first_air_date") or "N/A"
            return {
                'movie_id': data.get("id"),
                'title': title,
                'poster': poster_url,
                'rating': round(raw_rating, 1) if raw_rating else 0.0,
                'year': date_str[:4],
                'overview': data.get("overview", ""),
                'media_type': media_type
            }
    except Exception:
        st.toast("⚠️ Error fetching media info.", icon="⚠️")
    return None

@st.cache_data(show_spinner=False, ttl=86400)
def get_recommendations_from_tmdb(media_id, genre_filter="All", media_type="movie"):
    genre_mapping = {
        "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, 
        "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751, 
        "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402, 
        "Mystery": 9648, "Romance": 10749, "Science Fiction": 878, 
        "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37
    }
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/recommendations?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            recommendations = []
            target_genre_id = genre_mapping.get(genre_filter) if genre_filter != "All" else None
            
            for item in results:
                if target_genre_id and target_genre_id not in item.get("genre_ids", []):
                    continue
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                title = item.get("title") or item.get("name") or "Untitled"
                date_str = item.get("release_date") or item.get("first_air_date") or "N/A"
                recommendations.append({
                    'movie_id': item.get("id"),
                    'title': title,
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': date_str[:4],
                    'match': int(item.get("popularity", 50)) % 15 + 80,
                    'media_type': media_type
                })
            return recommendations
    except Exception:
        st.toast("⚠️ Error fetching recommendations.", icon="⚠️")
    return []

# --- Home page helpers ---
def format_tmdb_media(items, media_type="movie"):
    formatted = []
    for item in items or []:
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
        date_str = item.get("release_date") or item.get("first_air_date") or "N/A"
        rating = item.get("vote_average", 0.0) or 0.0
        formatted.append({
            "movie_id": item.get("id"),
            "title": item.get("title") or item.get("name") or "Untitled",
            "poster": poster_url,
            "rating": round(rating, 1),
            "year": date_str[:4] if date_str != "N/A" else "N/A",
            "match": min(99, int(item.get("popularity", 50)) % 15 + 80),
            "overview": item.get("overview", ""),
            "media_type": media_type
        })
    return formatted

@st.cache_data(show_spinner=False, ttl=86400)
def get_home_media(section, page=1):
    if section == "Trending Movies":
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}&language=en-US&page={page}"
        m_type = "movie"
    elif section == "Trending TV Shows":
        url = f"https://api.themoviedb.org/3/trending/tv/week?api_key={API_KEY}&language=en-US&page={page}"
        m_type = "tv"
    elif section == "Popular Anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16&with_original_language=ja&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Top Rated Anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16&with_original_language=ja&sort_by=vote_average.desc&vote_count.gte=50&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Action Anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16,10759&with_original_language=ja&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Fantasy Anime":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=16,10765&with_original_language=ja&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Top Rated Movies":
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={API_KEY}&language=en-US&page={page}"
        m_type = "movie"
    elif section == "Top Rated TV":
        url = f"https://api.themoviedb.org/3/tv/top_rated?api_key={API_KEY}&language=en-US&page={page}"
        m_type = "tv"
    elif section == "Action Movies":
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres=28&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "movie"
    elif section == "Horror Movies":
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres=27&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "movie"
    elif section == "Comedy Movies":
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres=35&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "movie"
    elif section == "Action TV":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=10759&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Drama TV":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=18&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    elif section == "Comedy TV":
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={API_KEY}&with_genres=35&sort_by=popularity.desc&page={page}&language=en-US"
        m_type = "tv"
    else:
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&sort_by=popularity.desc&language=en-US&page={page}"
        m_type = "movie"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return format_tmdb_media(response.json().get("results", []), media_type=m_type)
    except Exception:
        pass
    return []

def render_home_carousel(section, title, page_key):
    raw_media = get_home_media(section, st.session_state.get(page_key, 1))
    seen_ids = set()
    media_items = []
    for item in raw_media:
        m_id = item.get("movie_id")
        if m_id and m_id not in seen_ids:
            seen_ids.add(m_id)
            media_items.append(item)
    st.markdown(f'<div class="media-section-title">{title}</div>', unsafe_allow_html=True)
    if not media_items:
        st.info("This row could not load right now. Check connection and try again.")
        return
    offset_key = f"{page_key}_offset"
    offset = st.session_state.get(offset_key, 0)
    visible_count = 5
    max_offset = max(0, len(media_items) - visible_count)
    offset = min(offset, max_offset)
    left, center, right = st.columns([0.45, 10, 0.45], vertical_alignment="center")
    with left:
        if st.button("‹", key=f"{page_key}_left", help="Previous", disabled=offset <= 0):
            st.session_state[offset_key] = max(0, offset - 4)
            st.rerun()
    with center:
        shown = media_items[offset:offset + visible_count]
        cols = st.columns(len(shown))
        for i, item in enumerate(shown):
            with cols[i]:
                st.image(item["poster"], use_container_width=True)
                st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span> · {item["year"]}</div>', unsafe_allow_html=True)
                if st.button(item["title"], key=f"home_{page_key}_{item['movie_id']}_{offset}_{i}", use_container_width=True):
                    show_media_modal(item, prefix=f"home_{page_key}_{offset}_{i}")
    with right:
        if st.button("›", key=f"{page_key}_right", help="Next", disabled=offset >= max_offset):
            st.session_state[offset_key] = min(max_offset, offset + 4)
            st.rerun()

# --- Media Details Modal ---
@st.dialog("🎬 Details, Cast & Trailer", width="large")
def show_media_modal(item, prefix="modal"):
    m_type = item.get("media_type", "movie")
    overview, runtime, imdb_id, youtube_key, creator_director, cast = fetch_media_modal_data(item['movie_id'], media_type=m_type)
    providers = get_media_watch_providers(item['movie_id'], media_type=m_type)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(item['poster'], use_container_width=True)
        st.markdown(f"**Release Year:** {item['year']}")
        st.markdown(f"**Runtime / Format:** {runtime}")
        st.markdown(f"**Rating:** ⭐ {item['rating']}/10")
        st.markdown(f"**Type:** {m_type.upper()}")
        if imdb_id:
            st.markdown(f"[🔗 Open in IMDb](https://www.imdb.com/title/{imdb_id})")
        
        if "watchlist" not in st.session_state:
            st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
        
        is_in_watchlist = any(m['movie_id'] == item['movie_id'] and m.get('media_type', 'movie') == m_type for m in st.session_state.watchlist)
        if not is_in_watchlist:
            if st.button("❤️ Add to Watchlist", key=f"{prefix}_add_{item['movie_id']}"):
                watch_item = normalize_watchlist_item(item)
                watch_item['media_type'] = m_type
                if not any(m.get("movie_id") == watch_item.get("movie_id") and m.get('media_type') == m_type for m in st.session_state.watchlist):
                    st.session_state.watchlist.append(watch_item)
                if is_logged_in:
                    save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                    st.toast("Added to your saved Watchlist! ❤️", icon="✅")
                else:
                    st.toast("Added for this session. Sign in to keep it.", icon="ℹ️")
                st.rerun()
        else:
            if st.button("❌ Remove from Watchlist", key=f"{prefix}_rem_{item['movie_id']}"):
                st.session_state.watchlist = [m for m in st.session_state.watchlist if not (m['movie_id'] == item['movie_id'] and m.get('media_type', 'movie') == m_type)]
                save_user_watchlist(watchlist_owner, st.session_state.watchlist) if is_logged_in else None
                st.toast("Removed from watchlist.", icon="🗑️")
                st.rerun()
        
    with col2:
        st.subheader(f"{item['title']} ({item['year']})")
        creator_label = "Director" if m_type == "movie" else "Creator"
        st.markdown(f"🎬 **{creator_label}:** {creator_director}")
        st.markdown("**Overview / Storyline:**")
        st.write(overview)
        
        if cast:
            st.markdown("**👥 Top Cast (Click actor name to view filmography):**")
            cast_cols = st.columns(len(cast))
            for i, actor in enumerate(cast):
                with cast_cols[i]:
                    profile_path = actor.get("profile_path")
                    img_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else NO_IMAGE_URL
                    st.image(img_url, use_container_width=True)
                    
                    if st.button(f"👤 {actor.get('name')}", key=f"{prefix}_actor_{actor.get('id')}_{i}"):
                        st.session_state.main_nav_tab = "🎭 Actors & Directors"
                        st.session_state.top_menu_select = "Actors & Directors"
                        st.session_state.last_top_menu_choice = "Actors & Directors"
                        st.session_state.person_search_input = actor.get('name')
                        st.rerun()
        
        st.markdown("**📺 Where to Watch (Streaming):**")
        if providers:
            prov_cols = st.columns(min(len(providers), 4))
            for i, prov in enumerate(providers[:4]):
                with prov_cols[i]:
                    logo_path = prov.get("logo_path")
                    if logo_path:
                        st.image(f"https://image.tmdb.org/t/p/w92{logo_path}", width=45)
                    st.caption(prov.get("provider_name"))
        else:
            st.info("No online streaming providers available currently.")
        
        if youtube_key:
            st.markdown("**Official Trailer:**")
            st.video(f"https://www.youtube.com/watch?v={youtube_key}")
        else:
            st.info("No trailer video available.")

# Top navigation and account controls
if "main_nav_tab" not in st.session_state:
    st.session_state.main_nav_tab = "🏠 Home"

menu_options = {
    "Home": "🏠 Home",
    "Recommendations": "🍿 Discover & Recommendations",
    "Mood Finder": "🎲 Mood Finder",
    "Movie Franchises": "🎞️ Movie Franchises",
    "Actors & Directors": "🎭 Actors & Directors",
}
if "top_menu_select" not in st.session_state:
    st.session_state.top_menu_select = next((k for k, v in menu_options.items() if v == st.session_state.main_nav_tab), "Home")

nav_home, nav_watch, nav_menu, nav_account = st.columns([1.3, 1.1, 1.4, 1.3], vertical_alignment="center")
with nav_home:
    if st.button("🎬 Media Hub", use_container_width=True, key="top_home"):
        st.session_state.main_nav_tab = "🏠 Home"
        st.session_state.top_menu_select = "Home"
        st.session_state.last_top_menu_choice = "Home"
        st.rerun()
with nav_watch:
    if st.button("♡ Watchlist", use_container_width=True, key="top_watchlist"):
        st.session_state.main_nav_tab = "❤️ My Watchlist"
        st.session_state.top_menu_select = "Home"
        st.session_state.last_top_menu_choice = "Home"
        st.rerun()
with nav_menu:
    menu_choice = st.selectbox("☰ Menu", list(menu_options.keys()), key="top_menu_select", label_visibility="collapsed")
    if "last_top_menu_choice" not in st.session_state:
        st.session_state.last_top_menu_choice = menu_choice
    elif menu_choice != st.session_state.last_top_menu_choice:
        st.session_state.last_top_menu_choice = menu_choice
        mapped_choice = menu_options[menu_choice]
        st.session_state.main_nav_tab = mapped_choice
        st.rerun()
with nav_account:
    if is_logged_in:
        st.caption(f"👤 {user_name}")
        if st.button("Sign out", key="top_signout", use_container_width=True):
            st.logout()
    else:
        if st.button("Sign in", key="top_signin", use_container_width=True):
            try:
                st.login("google")
            except Exception:
                st.error("Google sign-in is not configured yet.")

# --- Enhanced Dedicated Search Bar Section ---
with st.container(border=True):
    st.markdown("##### 🔎 Universal Search & Discovery")
    with st.form("top_media_search_form", clear_on_submit=False):
        s_col1, s_col2, s_col3 = st.columns([1.5, 3.5, 1])
        with s_col1:
            top_search_type = st.selectbox("Search category", ["All", "Movies", "TV Shows", "Anime", "People", "Franchises"], key="top_search_type_widget", label_visibility="collapsed")
        with s_col2:
            top_search_query = st.text_input("Search query", placeholder="Type title, actor, franchise...", label_visibility="collapsed", key="top_search_query_widget")
        with s_col3:
            search_submitted = st.form_submit_button("Search 🚀", use_container_width=True)
            
        if search_submitted:
            cleaned_query = top_search_query.strip()
            if cleaned_query:
                st.session_state.top_search_results_query = cleaned_query
                st.session_state.top_search_media_type = top_search_type
                if top_search_type == "People":
                    st.session_state.person_search_input = cleaned_query
                    st.session_state.main_nav_tab = "🎭 Actors & Directors"
                    st.session_state.top_menu_select = "Actors & Directors"
                    st.session_state.last_top_menu_choice = "Actors & Directors"
                elif top_search_type == "Franchises":
                    st.session_state.franchise_search_input = cleaned_query
                    st.session_state.franchise_mode_radio = "Search Any Franchise 🔍"
                    st.session_state.main_nav_tab = "🎞️ Movie Franchises"
                    st.session_state.top_menu_select = "Movie Franchises"
                    st.session_state.last_top_menu_choice = "Movie Franchises"
                else:
                    st.session_state.main_nav_tab = "🔎 Media Search"
                    st.session_state.top_menu_select = "Home"
                    st.session_state.last_top_menu_choice = "Home"
                st.rerun()
            else:
                st.warning("Please enter a search term first.")

st.markdown("---")

num_recommendations = 6
sort_option = "Popularity / Match"
selected_genre = "All"
if st.session_state.main_nav_tab == "🍿 Discover & Recommendations":
    st.sidebar.header("⚙️ Recommendation Controls")
    num_recommendations = st.sidebar.slider("Number of Items:", min_value=3, max_value=20, value=6, key="num_movies_slider")
    sort_option = st.sidebar.selectbox("Sort Recommendations By:", ["Popularity / Match", "Highest Rating", "Release Year (Newest)"], key="sort_option_select")
    selected_genre = st.sidebar.selectbox("Filter by Genre:", ALL_GENRES, key="genre_filter_select")
    if st.sidebar.button("Surprise Me! 🎲", use_container_width=True, key="surprise_btn"):
        trending = get_home_media("Trending Movies")
        if trending:
            rand_item = random.choice(trending)
            st.session_state.selected_movie_id = rand_item.get("movie_id")
            with st.spinner(f'Surprise! Selecting "{rand_item.get("title")}"...'):
                st.session_state.selected_movie_info = get_media_details(rand_item.get("movie_id"), "movie")
                st.session_state.recommendations = get_recommendations_from_tmdb(rand_item.get("movie_id"), selected_genre, "movie")
            st.session_state.main_nav_tab = "🍿 Discover & Recommendations"
            st.rerun()
elif st.session_state.main_nav_tab == "🎲 Mood Finder":
    st.sidebar.header("🎲 Mood Results")
    num_recommendations = st.sidebar.slider("Number of Items:", min_value=3, max_value=20, value=6, key="mood_num_movies_slider")
    sort_option = st.sidebar.selectbox("Sort Mood Results By:", ["Popularity / Match", "Highest Rating", "Release Year (Newest)"], key="mood_sort_option_select")

main_tab_choice = st.session_state.main_nav_tab

if st.session_state.get("watchlist_owner") != watchlist_owner:
    st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
    st.session_state.watchlist_owner = watchlist_owner
elif "watchlist" not in st.session_state:
    st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
    st.session_state.watchlist_owner = watchlist_owner

# --- HOME with Correct Specific Categories & Filters ---
if main_tab_choice == "🏠 Home":
    st.title("🎬 Discover Movies, TV Shows & Anime")
    st.caption("Trending picks, top-rated movies, TV series, and anime — all in one unified hub.")
    
    home_filter = st.radio("Filter Home Categories:", ["All", "Movies", "TV Series", "Anime"], horizontal=True, key="home_category_filter")
    st.markdown("")

    if home_filter == "All":
        render_home_carousel("Trending Movies", "🔥 Trending Movies This Week", "home_trend_mov")
        render_home_carousel("Trending TV Shows", "📺 Trending TV Shows This Week", "home_trend_tv")
        render_home_carousel("Popular Anime", "🌸 Popular Anime Masterpieces", "home_anime")
        render_home_carousel("Action Movies", "💥 Action Movies", "home_act_mov")
        render_home_carousel("Horror Movies", "👻 Horror Movies", "home_hor_mov")
        render_home_carousel("Comedy Movies", "😂 Comedy Movies", "home_com_mov")
    elif home_filter == "Movies":
        render_home_carousel("Trending Movies", "🔥 Trending Movies This Week", "home_trend_mov")
        render_home_carousel("Top Rated Movies", "⭐ Top Rated Movies", "home_top_mov")
        render_home_carousel("Action Movies", "💥 Action Movies", "home_act_mov")
        render_home_carousel("Horror Movies", "👻 Horror Movies", "home_hor_mov")
        render_home_carousel("Comedy Movies", "😂 Comedy Movies", "home_com_mov")
    elif home_filter == "TV Series":
        render_home_carousel("Trending TV Shows", "📺 Trending TV Shows This Week", "home_trend_tv")
        render_home_carousel("Top Rated TV", "🌟 Top Rated TV Shows", "home_top_tv")
        render_home_carousel("Action TV", "⚔️ Action & Adventure TV", "home_act_tv")
        render_home_carousel("Drama TV", "🎭 Drama Series", "home_drm_tv")
        render_home_carousel("Comedy TV", "😄 Comedy Series", "home_com_tv")
    elif home_filter == "Anime":
        render_home_carousel("Popular Anime", "🌸 Popular Anime Masterpieces", "home_anime")
        render_home_carousel("Top Rated Anime", "⭐ Top Rated Anime", "home_top_anime")
        render_home_carousel("Action Anime", "⚔️ Action & Shonen Anime", "home_act_anime")
        render_home_carousel("Fantasy Anime", "✨ Fantasy & Sci-Fi Anime", "home_fan_anime")

# --- Global Search ---
elif main_tab_choice == "🔎 Media Search":
    st.title("🔎 Search Results")
    query = st.session_state.get("top_search_results_query", "")
    st_type = st.session_state.get("top_search_media_type", "All")
    
    if not query:
        st.info("Enter a title in the search bar above.")
    else:
        st.subheader(f"Results for ({st_type}): {query}")
        if st_type == "Movies":
            search_results = search_media_tmdb(query, media_type="Movies")
        elif st_type in ["TV Shows", "Anime"]:
            search_results = search_media_tmdb(query, media_type="TV Shows")
        else:
            search_results = search_media_tmdb(query, media_type="All")
            
        formatted_results = format_tmdb_media(search_results, media_type="movie")
        # Ensure proper media types are kept
        for i, res in enumerate(search_results):
            if i < len(formatted_results):
                formatted_results[i]["media_type"] = res.get("media_type", "movie")
                
        formatted_results = list({m["movie_id"]: m for m in formatted_results if m.get("movie_id")}.values())
        if not formatted_results:
            st.warning("No results found. Check your query and try again.")
        else:
            for row_start in range(0, len(formatted_results), 5):
                row_items = formatted_results[row_start:row_start + 5]
                cols = st.columns(len(row_items))
                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item["poster"], use_container_width=True)
                        st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span> · [{item.get("media_type","movie").upper()}]</div>', unsafe_allow_html=True)
                        if st.button(item["title"], key=f"top_search_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                            show_media_modal(item, prefix=f"top_search_{row_start + idx}")

# --- Recommendations ---
elif main_tab_choice == "🍿 Discover & Recommendations":
    st.title("🎯 Recommendations & Discover")
    st.caption("Get similar films and TV shows from a title you love, or use your watchlist.")
    rec_mode = st.radio("Recommendation source", ["From a Movie or TV Show", "Based on my Watchlist"], horizontal=True, key="recommendation_source_mode")
    search_query = ""
    media_sel_type = "movie"
    if rec_mode == "From a Movie or TV Show":
        m_type_col, q_col = st.columns([1, 3])
        with m_type_col:
            media_sel_type = st.selectbox("Type", ["movie", "tv"], key="rec_media_type_sel")
        with q_col:
            search_query = st.text_input("Search title for recommendations:", "Inception", key="global_search_input")

    selected_media_id = None
    if rec_mode == "From a Movie or TV Show" and search_query:
        search_results = search_media_tmdb(search_query, media_type="Movies" if media_sel_type=="movie" else "TV Shows")
        if search_results:
            media_options = []
            media_dict_map = {}
            for m in search_results:
                t = m.get("title") or m.get("name") or "Unknown"
                d = m.get("release_date") or m.get("first_air_date") or "N/A"
                year = d[:4] if d != "N/A" else "N/A"
                display_name = f"{t} ({year})" if year and year != "N/A" else t
                media_options.append(display_name)
                media_dict_map[display_name] = m.get("id")

            chosen_option = st.selectbox("Select from search results:", media_options, key="search_results_selectbox")
            selected_media_id = media_dict_map.get(chosen_option)
            st.session_state.selected_movie_id = selected_media_id

    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []

    rec_button_label = "Get Recommendations 🚀" if rec_mode == "From a Movie or TV Show" else "Recommend from My Watchlist ❤️"
    if st.button(rec_button_label, type="primary", key="get_recs_btn"):
        with st.spinner("Finding recommendations..."):
            if rec_mode == "From a Movie or TV Show" and selected_media_id:
                st.session_state.selected_movie_info = get_media_details(selected_media_id, media_sel_type)
                st.session_state.recommendations = get_recommendations_from_tmdb(selected_media_id, selected_genre, media_sel_type)
            elif rec_mode == "Based on my Watchlist":
                seeds = st.session_state.get("watchlist", [])
                if not seeds:
                    st.info("Your Watchlist is empty.")
                    st.session_state.recommendations = []
                else:
                    combined, seen = [], set()
                    for seed in seeds[:4]:
                        for rec in get_recommendations_from_tmdb(seed.get("movie_id"), selected_genre, seed.get("media_type", "movie")):
                            if rec.get("movie_id") not in seen and rec.get("movie_id") not in {x.get("movie_id") for x in seeds}:
                                combined.append(rec)
                                seen.add(rec.get("movie_id"))
                    st.session_state.selected_movie_info = None
                    st.session_state.recommendations = combined
            else:
                st.warning("Search and select a title first.")

    if "selected_movie_info" in st.session_state and st.session_state.selected_movie_info:
        sel_media = st.session_state.selected_movie_info
        st.markdown("---")
        st.subheader("🎯 Selected Title")

        col_img, col_info = st.columns([1, 4])
        with col_img:
            st.image(sel_media['poster'], width=180)
        with col_info:
            st.markdown(f"### {sel_media['title']} ({sel_media['year']})")
            st.markdown(f"⭐ **Rating:** {sel_media['rating']}/10")
            st.write(sel_media['overview'])
            if st.button(f"🎬 View Details", key="btn_selected_details"):
                show_media_modal(sel_media, prefix="selected")

        st.markdown("---")
        st.subheader("🍿 Recommended Media")

    if st.session_state.recommendations:
        results = st.session_state.recommendations.copy()
        if sort_option == "Popularity / Match":
            results = sorted(results, key=lambda x: x['match'], reverse=True)
        elif sort_option == "Highest Rating":
            results = sorted(results, key=lambda x: x['rating'], reverse=True)
        elif sort_option == "Release Year (Newest)":
            results = sorted(results, key=lambda x: x['year'], reverse=True)

        results = results[:num_recommendations]
        COLS_PER_ROW = 5
        for row_start in range(0, len(results), COLS_PER_ROW):
            row_items = results[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span> | <span class="media-match">🎯 {item["match"]}%</span></div>', unsafe_allow_html=True)
                    if st.button(f"{item['title']} ({item['year']})", key=f"btn_recs_{item['movie_id']}_{row_start + idx}"):
                        show_media_modal(item, prefix=f"recs_{row_start + idx}")

# --- Mood Finder ---
elif main_tab_choice == "🎲 Mood Finder":
    st.title("🎲 Mood Finder (Movies, TV & Anime)")
    st.caption("Choose what kind of experience you want tonight.")
    mood_media_type = st.selectbox("Category:", ["Movies", "TV Shows", "Anime"], key="mood_category_sel")
    selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()), key="mood_selector")

    if "mood_page" not in st.session_state:
        st.session_state.mood_page = 1

    if st.button("Find Media by Mood 🎯", type="primary", key="mood_btn"):
        st.session_state.mood_page = 1

    mood_data = MOOD_OPTIONS[selected_mood]
    m_type_map = {"Movies": "movie", "TV Shows": "tv", "Anime": "anime"}

    with st.spinner("Finding media matching your mood..."):
        mood_media, total_mood_pages = discover_media_by_mood(mood_data["genres"], mood_data["sort"], media_type=m_type_map[mood_media_type], page=st.session_state.mood_page)

    if not mood_media:
        st.info("No results loaded for this mood right now.")
    if mood_media:
        if sort_option == "Highest Rating":
            mood_media = sorted(mood_media, key=lambda x: x.get("rating", 0), reverse=True)
        elif sort_option == "Release Year (Newest)":
            mood_media = sorted(mood_media, key=lambda x: x.get("year", "0000"), reverse=True)
        else:
            mood_media = sorted(mood_media, key=lambda x: x.get("match", 0), reverse=True)
        mood_media = mood_media[:num_recommendations]
        col_m1, col_m2 = st.columns([2, 3])
        with col_m1:
            st.markdown(f"### 🌟 Mood Recommendations")
        with col_m2:
            if total_mood_pages > 1:
                st.session_state.mood_page = st.selectbox("Select Page:", range(1, total_mood_pages + 1), index=st.session_state.mood_page - 1, key="mood_page_selector")

        COLS_PER_ROW = 5
        for row_start in range(0, len(mood_media), COLS_PER_ROW):
            row_items = mood_media[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                    if st.button(f"{item['title']} ({item['year']})", key=f"btn_mood_{item['movie_id']}_{row_start + idx}"):
                        show_media_modal(item, prefix=f"mood_{row_start + idx}")

# --- Actors & Directors ---
elif main_tab_choice == "🎭 Actors & Directors":
    st.title("🎭 Actors, Directors & Creators")
    st.caption("Search performers and creators, and filter out talk shows or interviews.")
    person_query = st.text_input("Search for actor, director or creator:", key="person_search_input")

    if st.session_state.get("last_person_query") != person_query:
        st.session_state.last_person_query = person_query
        st.session_state.person_movies = []
        st.session_state.loaded_person_id = None
        st.session_state.person_page = 1

    selected_person_id = None
    selected_person = None
    if person_query:
        person_results = search_person_tmdb(person_query)
        if person_results:
            person_options = {f"{p.get('name')} ({p.get('known_for_department', 'Artist')} - Pop: {round(p.get('popularity', 0), 1)})": p for p in person_results}
            chosen_person = st.selectbox("Select Person:", list(person_options.keys()), key="person_selectbox")
            selected_person = person_options.get(chosen_person)
            selected_person_id = selected_person.get('id') if selected_person else None

    if selected_person:
        person_details = get_person_details(selected_person.get("id")) if selected_person.get("id") else {}
        profile_path = person_details.get("profile_path") or selected_person.get("profile_path")
        profile_url = f"https://image.tmdb.org/t/p/w342{profile_path}" if profile_path else NO_IMAGE_URL
        profile_col, details_col = st.columns([1, 3], vertical_alignment="top")
        with profile_col:
            st.image(profile_url, use_container_width=True)
        with details_col:
            st.markdown(f"### {person_details.get('name') or selected_person.get('name', 'Unknown')}")
            st.write(f"**Department:** {person_details.get('known_for_department') or selected_person.get('known_for_department', 'Not listed')}")
            if person_details.get("birthday"):
                st.markdown(f"**Born:** {person_details['birthday']}")
            biography = (person_details.get("biography") or "").strip()
            if biography:
                st.markdown("**Biography**")
                st.write(biography)

    if selected_person_id:
        should_load_filmography = st.session_state.get("loaded_person_id") != selected_person_id
        if should_load_filmography or st.button("Show Full Filmography 🎥", type="primary", key="person_btn"):
            st.session_state.person_page = 1
            with st.spinner("Loading complete filmography..."):
                st.session_state.person_movies = get_person_filmography(selected_person_id)
                st.session_state.loaded_person_id = selected_person_id

    if (selected_person_id and st.session_state.get("loaded_person_id") == selected_person_id and st.session_state.get("person_movies")):
        st.markdown("---")
        
        # Filter bar for filmography types (Movies, TV Series, All)
        filmography_filter = st.radio("Filter Works:", ["All Works", "Movies Only", "TV Series Only"], horizontal=True, key="filmography_type_filter")
        
        all_p_movies = st.session_state.person_movies
        if filmography_filter == "Movies Only":
            all_p_movies = [m for m in all_p_movies if m.get("media_type") == "movie"]
        elif filmography_filter == "TV Series Only":
            all_p_movies = [m for m in all_p_movies if m.get("media_type") == "tv"]
            
        total_items = len(all_p_movies)
        items_per_page = 15
        total_p_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        col_p1, col_p2 = st.columns([2, 3])
        with col_p1:
            st.markdown(f"### 🎬 Filtered Works ({total_items} Items)")
        with col_p2:
            if total_p_pages > 1:
                st.session_state.person_page = st.selectbox("Select Page:", range(1, total_p_pages + 1), index=min(st.session_state.person_page - 1, total_p_pages - 1), key="person_page_selector")

        start_idx = (st.session_state.person_page - 1) * items_per_page
        page_movies = all_p_movies[start_idx:start_idx + items_per_page]

        if not page_movies:
            st.info("No items match this filter.")
        else:
            COLS_PER_ROW = 5
            for row_start in range(0, len(page_movies), COLS_PER_ROW):
                row_items = page_movies[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                for idx, item in enumerate(row_items):
                    global_idx = start_idx + row_start + idx
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span> [{item["media_type"].upper()}]</div>', unsafe_allow_html=True)
                        if st.button(f"{global_idx + 1}. {item['title']} ({item['year']})", key=f"btn_person_{item['movie_id']}_{global_idx}"):
                            show_media_modal(item, prefix=f"person_{global_idx}")

# --- Movie Franchises ---
elif main_tab_choice == "🎞️ Movie Franchises":
    st.title("🎞️ Movie Franchises & Collections")
    st.caption("Browse popular movie collections and cinematic universes.")
    search_mode = st.radio("Choose exploration mode:", ["Popular Franchises ⭐", "Search Any Franchise 🔍"], horizontal=True, key="franchise_mode_radio")

    selected_coll_id = None
    if search_mode == "Popular Franchises ⭐":
        preset_choice = st.selectbox("Select a Popular Franchise:", list(POPULAR_COLLECTIONS.keys()), key="preset_franchise_sel")
        selected_coll_id = POPULAR_COLLECTIONS.get(preset_choice)
    else:
        franchise_query = st.text_input("Search for any Franchise / Collection:", "", key="franchise_search_input")
        if franchise_query:
            coll_results = search_collection_tmdb(franchise_query)
            if coll_results:
                coll_options = {c.get("name"): c.get("id") for c in coll_results if c.get("name") and c.get("id")}
                if coll_options:
                    coll_names = list(coll_options.keys())
                    chosen_coll_name = st.selectbox("Select Collection:", coll_names, key="coll_selectbox")
                    selected_coll_id = coll_options.get(chosen_coll_name)

    if selected_coll_id:
        with st.spinner("Fetching franchise chronologically..."):
            collection = get_collection_details(selected_coll_id)
            if collection:
                st.markdown("---")
                col_c1, col_c2 = st.columns([1, 4])
                with col_c1:
                    st.image(collection['poster'], width=180)
                with col_c2:
                    st.markdown(f"## {collection['name']}")
                    st.markdown(f"**Total Movies:** {len(collection['parts'])}")
                    st.write(collection['overview'])

                st.markdown("### 🎬 Movies in Chronological Order:")
                parts = collection['parts']
                COLS_PER_ROW = 5
                for row_start in range(0, len(parts), COLS_PER_ROW):
                    row_items = parts[row_start : row_start + COLS_PER_ROW]
                    cols = st.columns(COLS_PER_ROW)
                    for idx, item in enumerate(row_items):
                        with cols[idx]:
                            st.image(item['poster'], use_container_width=True)
                            st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                            if st.button(f"{idx + row_start + 1}. {item['title']} ({item['year']})", key=f"btn_coll_{item['movie_id']}_{row_start + idx}"):
                                show_media_modal(item, prefix=f"coll_{row_start + idx}")

# --- My Watchlist ---
elif main_tab_choice == "❤️ My Watchlist":
    st.title(f"❤️ {user_name}'s Watchlist")
    st.caption("Track movies, TV shows, and anime you want to watch or have watched.")
    if not is_logged_in:
        st.info("Guest Watchlist lasts for this browser session.")
    elif not supabase_storage_enabled():
        st.info("Cloud database is not configured. Using local JSON storage.")
    if not st.session_state.watchlist:
        st.info("Your Watchlist is empty. Add items using 'Add to Watchlist'.")
    else:
        statuses = ["All", "Want to Watch", "Watching", "Watched"]
        status_filter = st.selectbox("Filter by status", statuses, key="watchlist_status_filter")
        watchlist_items = [normalize_watchlist_item(m) for m in st.session_state.watchlist]
        if status_filter != "All":
            watchlist_items = [m for m in watchlist_items if m.get("status"] == status_filter]
        st.markdown(f"**{len(watchlist_items)}** items in view · **{len(st.session_state.watchlist)}** total saved")
        
        COLS_PER_ROW = 5
        for row_start in range(0, len(watchlist_items), COLS_PER_ROW):
            row_items = watchlist_items[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW, gap="medium")
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="media-info"><span class="media-rating">⭐ {item["rating"]}/10</span> · [{item.get("media_type","movie").upper()}]</div>', unsafe_allow_html=True)
                        if st.button(f"{item['title']}", key=f"btn_watch_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                            show_media_modal(item, prefix=f"watch_{row_start + idx}")
                        st.caption(f"📌 {item.get('status', 'Want to Watch')}")
                        with st.expander("✏️ Edit tracker"):
                            status_options = ["Want to Watch", "Watching", "Watched"]
                            new_status = st.selectbox("Status", status_options, index=status_options.index(item["status"]) if item["status"] in status_options else 0, key=f"wl_status_{item['movie_id']}_{row_start+idx}")
                            new_rating = st.slider("Rating", 0, 10, int(item.get("personal_rating", 0) or 0), key=f"wl_rating_{item['movie_id']}_{row_start+idx}")
                            new_note = st.text_input("Note", value=item.get("note", ""), key=f"wl_note_{item['movie_id']}_{row_start+idx}")
                            if (new_status != item["status"] or new_rating != int(item.get("personal_rating", 0) or 0) or new_note != item.get("note", "")):
                                for saved in st.session_state.watchlist:
                                    if saved.get("movie_id") == item.get("movie_id") and saved.get("media_type") == item.get("media_type"):
                                        saved["status"] = new_status
                                        saved["personal_rating"] = new_rating
                                        saved["note"] = new_note
                                        break
                                if is_logged_in:
                                    save_user_watchlist(watchlist_owner, st.session_state.watchlist)
        st.markdown("---")
        if st.button("🗑️ Clear Entire Watchlist", type="secondary", key="clear_watchlist_all"):
            st.session_state.watchlist = []
            save_user_watchlist(watchlist_owner, st.session_state.watchlist) if is_logged_in else None
            st.toast("Watchlist cleared.", icon="🧹")
            st.rerun()
