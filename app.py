import streamlit as st
import requests
import random
import time
import json
import os

# 1. Page Configuration
st.set_page_config(
    page_title="Smart Live Movie & Franchise Hub",
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
    .movie-section-title { font-size: 1.45rem; font-weight: 800; margin: 1.2rem 0 .35rem; }
    .home-subtitle { color: #b8b8c4; margin-top: -.5rem; }
    .movie-section-title { border-left: 4px solid #f5c518; padding-left: .65rem; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
    .top-brand { font-size: 1.35rem; font-weight: 900; letter-spacing: -.4px; }
    .top-brand span { color: #f5c518; }
    div.stButton > button[kind="secondary"] { background: #19191f; border: 1px solid #35353d; }
    [data-testid="stCaptionContainer"] { color: #b8b8c4; }
    @media (max-width: 760px) {
        .block-container { padding-left: .7rem; padding-right: .7rem; }
        .movie-section-title { font-size: 1.1rem; }
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

# Optional persistent storage for hosted deployments.
# Keep the Supabase service-role key in Streamlit secrets only; never commit it to source control.
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

# Local JSON fallback is useful for development. Hosted deployments should configure Supabase.
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
        st.warning("Could not save the Watchlist locally. On hosted deployments, configure Supabase for reliable persistence.")
        return False

def normalize_watchlist_item(item):
    """Keep older watchlist entries compatible with the newer tracker fields."""
    normalized = dict(item)
    normalized.setdefault("status", "Want to Watch")
    normalized.setdefault("personal_rating", 0)
    normalized.setdefault("note", "")
    return normalized

# 4. Optional Google Authentication
# Visitors can browse without signing in. Google login is only needed for an account-based watchlist.
try:
    is_logged_in = bool(st.user.is_logged_in)
except Exception:
    is_logged_in = False

if is_logged_in:
    user_email = st.user.get("email", "user@gmail.com")
    user_name = st.user.get("name", "Movie Fan")
    watchlist_owner = user_email
else:
    user_email = ""
    user_name = "Guest"
    # Guest list is temporary for this browser session; account lists persist per email.
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

# --- API Functions with Optimized Caching TTL ---

@st.cache_data(show_spinner=False, ttl=86400)
def search_movie_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        st.toast(f"⚠️ Connection error during search: {e}", icon="🚨")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_trending_movies():
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception:
        st.toast("⚠️ Unable to fetch trending movies.", icon="⚠️")
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
    """Fetch biography and personal details for an actor/director from TMDB."""
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
    url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            all_movies_dict = {}
            for m in data.get("cast", []) + data.get("crew", []):
                m_id = m.get("id")
                if m_id and m_id not in all_movies_dict:
                    all_movies_dict[m_id] = m
                    
            sorted_movies = sorted(list(all_movies_dict.values()), key=lambda x: x.get("popularity", 0), reverse=True)
            formatted_movies = []
            for item in sorted_movies:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                formatted_movies.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': item.get("release_date", "N/A")[:4]
                })
            return formatted_movies
    except Exception:
        st.toast("⚠️ Error fetching actor filmography.", icon="⚠️")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def discover_movies_by_mood(genre_ids, sort_by, page=1):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_ids}&sort_by={sort_by}&page={page}&language=en-US&vote_count.gte=100&vote_average.gte=5.5"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            total_pages = min(data.get("total_pages", 1), 10)
            movies = []
            for item in results:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                movies.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': item.get("release_date", "N/A")[:4],
                    'match': int(item.get("popularity", 50)) % 15 + 80
                })
            return movies, total_pages
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
                    'year': item.get("release_date", "N/A")[:4],
                    'overview': item.get("overview", "")
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
def fetch_movie_modal_data(movie_id):
    info_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}&language=en-US"
    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}&language=en-US"
    
    overview, runtime, imdb_id, youtube_key, director, cast = "No overview available.", "N/A", None, None, "N/A", []
    try:
        res_info = requests.get(info_url, timeout=5)
        if res_info.status_code == 200:
            data = res_info.json()
            overview = data.get("overview", "No overview available.")
            runtime = f"{data.get('runtime', 0)} mins"
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
                if person.get("job") == "Director":
                    director = person.get("name")
                    break
            cast = c_data.get("cast", [])[:4]
    except Exception:
        st.toast("⚠️ Error loading modal content.", icon="⚠️")
    return overview, runtime, imdb_id, youtube_key, director, cast

@st.cache_data(show_spinner=False, ttl=86400)
def get_movie_watch_providers(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={API_KEY}"
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
def get_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            poster_path = data.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
            raw_rating = data.get("vote_average", 0.0)
            return {
                'movie_id': data.get("id"),
                'title': data.get("title"),
                'poster': poster_url,
                'rating': round(raw_rating, 1) if raw_rating else 0.0,
                'year': data.get("release_date", "N/A")[:4],
                'overview': data.get("overview", "")
            }
    except Exception:
        st.toast("⚠️ Error fetching movie info.", icon="⚠️")
    return None

@st.cache_data(show_spinner=False, ttl=86400)
def get_recommendations_from_tmdb(movie_id, genre_filter="All"):
    genre_mapping = {
        "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, 
        "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751, 
        "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402, 
        "Mystery": 9648, "Romance": 10749, "Science Fiction": 878, 
        "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37
    }
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={API_KEY}&language=en-US"
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
                recommendations.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': round(raw_rating, 1) if raw_rating else 0.0,
                    'year': item.get("release_date", "N/A")[:4],
                    'match': int(item.get("popularity", 50)) % 15 + 80
                })
            return recommendations
    except Exception:
        st.toast("⚠️ Error fetching recommendations.", icon="⚠️")
    return []

# --- Home page helpers ---
def format_tmdb_movies(items):
    formatted = []
    for item in items or []:
        poster_path = item.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
        release_date = item.get("release_date") or "N/A"
        rating = item.get("vote_average", 0.0) or 0.0
        formatted.append({
            "movie_id": item.get("id"),
            "title": item.get("title") or item.get("name") or "Untitled",
            "poster": poster_url,
            "rating": round(rating, 1),
            "year": release_date[:4] if release_date != "N/A" else "N/A",
            "match": min(99, int(item.get("popularity", 50)) % 15 + 80),
            "overview": item.get("overview", "")
        })
    return formatted

@st.cache_data(show_spinner=False, ttl=86400)
def get_home_movies(section, page=1):
    if section == "Trending":
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}&language=en-US&page={page}"
    elif section == "Top Rated":
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={API_KEY}&language=en-US&page={page}"
    else:
        genre_ids = {"Action": 28, "Horror": 27, "Animation": 16, "Drama": 18, "Comedy": 35, "Adventure": 12, "Thriller": 53}
        genre_id = genre_ids.get(section, 28)
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&language=en-US&page={page}"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return format_tmdb_movies(response.json().get("results", []))
    except Exception:
        pass
    return []

def render_home_carousel(section, title, page_key):
    raw_movies = get_home_movies(section, st.session_state.get(page_key, 1))
    seen_ids = set()
    movies = []
    for movie in raw_movies:
        movie_id = movie.get("movie_id")
        if movie_id and movie_id not in seen_ids:
            seen_ids.add(movie_id)
            movies.append(movie)
    st.markdown(f'<div class="movie-section-title">{title}</div>', unsafe_allow_html=True)
    if not movies:
        st.info("This row could not load right now. Check the TMDB API key and connection, then try again.")
        return
    offset_key = f"{page_key}_offset"
    offset = st.session_state.get(offset_key, 0)
    visible_count = 5
    max_offset = max(0, len(movies) - visible_count)
    offset = min(offset, max_offset)
    left, center, right = st.columns([0.45, 10, 0.45], vertical_alignment="center")
    with left:
        if st.button("‹", key=f"{page_key}_left", help="Previous movies", disabled=offset <= 0):
            st.session_state[offset_key] = max(0, offset - 4)
            st.rerun()
    with center:
        shown = movies[offset:offset + visible_count]
        cols = st.columns(len(shown))
        for i, movie in enumerate(shown):
            with cols[i]:
                st.image(movie["poster"], use_container_width=True)
                st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {movie["rating"]}/10</span> · {movie["year"]}</div>', unsafe_allow_html=True)
                if st.button(movie["title"], key=f"home_{page_key}_{movie['movie_id']}_{offset}", use_container_width=True):
                    show_movie_modal(movie, prefix=f"home_{page_key}_{offset}_{i}")
    with right:
        if st.button("›", key=f"{page_key}_right", help="Next movies", disabled=offset >= max_offset):
            st.session_state[offset_key] = min(max_offset, offset + 4)
            st.rerun()

# --- Movie Details Modal ---
@st.dialog("🎬 Movie Details, Cast & Trailer", width="large")
def show_movie_modal(item, prefix="modal"):
    overview, runtime, imdb_id, youtube_key, director, cast = fetch_movie_modal_data(item['movie_id'])
    providers = get_movie_watch_providers(item['movie_id'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(item['poster'], use_container_width=True)
        st.markdown(f"**Release Year:** {item['year']}")
        st.markdown(f"**Runtime:** {runtime}")
        st.markdown(f"**Rating:** ⭐ {item['rating']}/10")
        if imdb_id:
            st.markdown(f"[🔗 Open in IMDb](https://www.imdb.com/title/{imdb_id})")
        
        if "watchlist" not in st.session_state:
            st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
        
        is_in_watchlist = any(m['movie_id'] == item['movie_id'] for m in st.session_state.watchlist)
        if not is_in_watchlist:
            if st.button("❤️ Add to Watchlist", key=f"{prefix}_add_{item['movie_id']}"):
                watch_item = normalize_watchlist_item(item)
                if not any(m.get("movie_id") == watch_item.get("movie_id") for m in st.session_state.watchlist):
                    st.session_state.watchlist.append(watch_item)
                if is_logged_in:
                    save_user_watchlist(watchlist_owner, st.session_state.watchlist)
                    st.toast("Added to your saved Watchlist! ❤️", icon="✅")
                else:
                    st.toast("Added for this session. Sign in to keep it between visits.", icon="ℹ️")
                st.rerun()
        else:
            if st.button("❌ Remove from Watchlist", key=f"{prefix}_rem_{item['movie_id']}"):
                st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                save_user_watchlist(watchlist_owner, st.session_state.watchlist) if is_logged_in else None
                st.toast("Removed from watchlist.", icon="🗑️")
                st.rerun()
        
    with col2:
        st.subheader(f"{item['title']} ({item['year']})")
        st.markdown(f"🎬 **Director:** {director}")
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
            st.info("No online streaming providers available for this movie currently.")
        
        if youtube_key:
            st.markdown("**Official Trailer:**")
            st.video(f"https://www.youtube.com/watch?v={youtube_key}")
        else:
            st.info("No trailer video available for this movie.")

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

nav_home, nav_watch, nav_search, nav_menu, nav_account = st.columns([1.45, 1.05, 2.35, 1.75, 1.55], vertical_alignment="center")
with nav_home:
    if st.button("🎬 Smart Movie", use_container_width=True, key="top_home"):
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
with nav_search:
    with st.form("top_movie_search_form", clear_on_submit=False):
        kind_col, qcol, bcol = st.columns([1.35, 3.2, 0.7])
        with kind_col:
            top_search_type = st.selectbox("Search type", ["Movies", "People", "Franchises"], key="top_search_type", label_visibility="collapsed")
        with qcol:
            top_search_query = st.text_input("Search", placeholder="Movie, person, franchise…", label_visibility="collapsed", key="top_search_query")
        with bcol:
            search_submitted = st.form_submit_button("🔎", use_container_width=True)
        if search_submitted:
            cleaned_query = top_search_query.strip()
            st.session_state.top_search_results_query = cleaned_query
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
                st.session_state.main_nav_tab = "🔎 Movie Search"
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
                st.error("Google sign-in is not configured yet. You can still browse the site as a guest.")

st.markdown("---")

# Recommendation controls appear only on pages that use them.
num_recommendations = 6
sort_option = "Popularity / Match"
selected_genre = "All"
if st.session_state.main_nav_tab == "🍿 Discover & Recommendations":
    st.sidebar.header("⚙️ Recommendation Controls")
    num_recommendations = st.sidebar.slider("Number of Movies:", min_value=3, max_value=20, value=6, key="num_movies_slider")
    sort_option = st.sidebar.selectbox("Sort Recommendations By:", ["Popularity / Match", "Highest Rating", "Release Year (Newest)"], key="sort_option_select")
    selected_genre = st.sidebar.selectbox("Filter by Genre:", ALL_GENRES, key="genre_filter_select")
    if st.sidebar.button("Surprise Me! 🎲", use_container_width=True, key="surprise_btn"):
        trending = get_trending_movies()
        if trending:
            rand_movie = random.choice(trending)
            st.session_state.selected_movie_id = rand_movie.get("id")
            with st.spinner(f'Surprise! Selecting "{rand_movie.get("title")}"...'):
                st.session_state.selected_movie_info = get_movie_details(rand_movie.get("id"))
                st.session_state.recommendations = get_recommendations_from_tmdb(rand_movie.get("id"), selected_genre)
            st.session_state.main_nav_tab = "🍿 Discover & Recommendations"
            st.rerun()
elif st.session_state.main_nav_tab == "🎲 Mood Finder":
    st.sidebar.header("🎲 Mood Results")
    num_recommendations = st.sidebar.slider("Number of Movies:", min_value=3, max_value=20, value=6, key="mood_num_movies_slider")
    sort_option = st.sidebar.selectbox("Sort Mood Results By:", ["Popularity / Match", "Highest Rating", "Release Year (Newest)"], key="mood_sort_option_select")

main_tab_choice = st.session_state.main_nav_tab

if st.session_state.get("watchlist_owner") != watchlist_owner:
    st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
    st.session_state.watchlist_owner = watchlist_owner
elif "watchlist" not in st.session_state:
    st.session_state.watchlist = [normalize_watchlist_item(m) for m in load_user_watchlist(watchlist_owner)] if is_logged_in else []
    st.session_state.watchlist_owner = watchlist_owner

# --- HOME: Netflix-style horizontal movie rows ---
if main_tab_choice == "🏠 Home":
    # Keep Home focused on browsing; discovery pages are already available in the menu.
    st.title("🎬 Discover Movies")
    st.caption("Trending picks, genre favorites, and top-rated movies — all in one place.")
    render_home_carousel("Trending", "🔥 Trending This Week", "home_trending")
    render_home_carousel("Action", "💥 Action & Adventure", "home_action")
    render_home_carousel("Horror", "👻 Horror", "home_horror")
    render_home_carousel("Animation", "🍿 Animation & Cartoons", "home_animation")
    render_home_carousel("Drama", "🎭 Drama", "home_drama")
    render_home_carousel("Comedy", "😂 Comedy", "home_comedy")
    render_home_carousel("Thriller", "🕵️ Thriller & Mystery", "home_thriller")
    render_home_carousel("Adventure", "🧭 Adventure", "home_adventure")
    render_home_carousel("Top Rated", "⭐ Top Rated", "home_toprated")

# --- Global movie search from the top bar ---
elif main_tab_choice == "🔎 Movie Search":
    st.title("🔎 Search Movies")
    query = st.session_state.get("top_search_results_query", "")
    if not query:
        st.info("Enter a movie title in the search bar above.")
    else:
        st.subheader(f"Results for: {query}")
        search_results = search_movie_tmdb(query)
        formatted_results = format_tmdb_movies(search_results)
        formatted_results = list({m["movie_id"]: m for m in formatted_results if m.get("movie_id")}.values())
        if not formatted_results:
            st.warning("No movies found, or TMDB could not be reached. Check your connection/API key and try again.")
        else:
            for row_start in range(0, len(formatted_results), 5):
                row_items = formatted_results[row_start:row_start + 5]
                cols = st.columns(len(row_items))
                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item["poster"], use_container_width=True)
                        st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span> · {item["year"]}</div>', unsafe_allow_html=True)
                        if st.button(item["title"], key=f"top_search_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                            show_movie_modal(item, prefix=f"top_search_{row_start + idx}")

# --- Movie-based Recommendations ---
elif main_tab_choice == "🍿 Discover & Recommendations":
    st.title("🎯 Movie Recommendations")
    st.caption("Get similar films from a title you love, or use your saved watchlist as a starting point.")
    rec_mode = st.radio("Recommendation source", ["From a movie", "Based on my Watchlist"], horizontal=True, key="recommendation_source_mode")
    search_query = ""
    if rec_mode == "From a movie":
        search_query = st.text_input("Search movie to get tailored recommendations:", "Obsession", key="global_search_input")

    selected_movie_id = None
    if rec_mode == "From a movie" and search_query:
        search_results = search_movie_tmdb(search_query)
        if search_results:
            movie_options = []
            movie_dict_map = {}
            for m in search_results:
                title = m.get("title", "Unknown")
                year = m.get("release_date", "N/A")[:4]
                display_name = f"{title} ({year})" if year and year != "N/A" else title
                movie_options.append(display_name)
                movie_dict_map[display_name] = m.get("id")

            chosen_option = st.selectbox("Select from search results:", movie_options, key="search_results_selectbox")
            selected_movie_id = movie_dict_map.get(chosen_option)
            st.session_state.selected_movie_id = selected_movie_id

    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []

    rec_button_label = "Get Recommendations 🚀" if rec_mode == "From a movie" else "Recommend from My Watchlist ❤️"
    if st.button(rec_button_label, type="primary", key="get_recs_btn"):
        with st.spinner("Finding movies you may like..."):
            if rec_mode == "From a movie" and selected_movie_id:
                st.session_state.selected_movie_info = get_movie_details(selected_movie_id)
                st.session_state.recommendations = get_recommendations_from_tmdb(selected_movie_id, selected_genre)
            elif rec_mode == "Based on my Watchlist":
                seeds = st.session_state.get("watchlist", [])
                if not seeds:
                    st.info("Your Watchlist is empty. Add a few movies first, or choose 'From a movie'.")
                    st.session_state.recommendations = []
                else:
                    combined, seen = [], set()
                    for seed in seeds[:4]:
                        for rec in get_recommendations_from_tmdb(seed.get("movie_id"), selected_genre):
                            if rec.get("movie_id") not in seen and rec.get("movie_id") not in {x.get("movie_id") for x in seeds}:
                                combined.append(rec)
                                seen.add(rec.get("movie_id"))
                    st.session_state.selected_movie_info = None
                    st.session_state.recommendations = combined
            else:
                st.warning("Search for a movie and select a result first.")

    if "selected_movie_info" in st.session_state and st.session_state.selected_movie_info:
        sel_movie = st.session_state.selected_movie_info
        st.markdown("---")
        st.subheader("🎯 Selected Movie")

        col_img, col_info = st.columns([1, 4])
        with col_img:
            st.image(sel_movie['poster'], width=180)
        with col_info:
            st.markdown(f"### {sel_movie['title']} ({sel_movie['year']})")
            st.markdown(f"⭐ **Rating:** {sel_movie['rating']}/10")
            st.write(sel_movie['overview'])
            if st.button(f"🎬 View Details: {sel_movie['title']}", key="btn_selected_details"):
                show_movie_modal(sel_movie, prefix="selected")

        st.markdown("---")
        st.subheader("🍿 Recommended Movies")

    if st.session_state.recommendations:
        results = st.session_state.recommendations.copy()

        if sort_option == "Popularity / Match":
            results = sorted(results, key=lambda x: x['match'], reverse=True)
        elif sort_option == "Highest Rating":
            results = sorted(results, key=lambda x: x['rating'], reverse=True)
        elif sort_option == "Release Year (Newest)":
            results = sorted(results, key=lambda x: x['year'], reverse=True)

        results = results[:num_recommendations]

        if not results:
            st.warning(f"⚠️ No recommendations found matching genre '{selected_genre}'.")
        else:
            COLS_PER_ROW = 5
            for row_start in range(0, len(results), COLS_PER_ROW):
                row_items = results[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)

                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(
                            f'<div class="movie-info">'
                            f'<span class="movie-rating">⭐ {item["rating"]}/10</span> | '
                            f'<span class="movie-match">🎯 {item["match"]}%</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        if st.button(f"{item['title']} ({item['year']})", key=f"btn_recs_{item['movie_id']}_{row_start + idx}"):
                            show_movie_modal(item, prefix=f"recs_{row_start + idx}")



# --- Mood Finder ---
elif main_tab_choice == "🎲 Mood Finder":
    st.title("🎲 Mood Finder")
    st.caption("Choose the kind of experience you want tonight. Results are filtered for a minimum rating and vote count when TMDB provides that data.")
    st.subheader("🎲 What are you in the mood for?")
    selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()), key="mood_selector")

    if "mood_page" not in st.session_state:
        st.session_state.mood_page = 1

    if st.button("Find Movies by Mood 🎯", type="primary", key="mood_btn"):
        st.session_state.mood_page = 1

    mood_data = MOOD_OPTIONS[selected_mood]

    with st.spinner("Finding movies matching your mood..."):
        mood_movies, total_mood_pages = discover_movies_by_mood(mood_data["genres"], mood_data["sort"], page=st.session_state.mood_page)

    if not mood_movies:
        st.info("No results loaded for this mood right now. Try again or select another mood.")
    if mood_movies:
        if sort_option == "Highest Rating":
            mood_movies = sorted(mood_movies, key=lambda x: x.get("rating", 0), reverse=True)
        elif sort_option == "Release Year (Newest)":
            mood_movies = sorted(mood_movies, key=lambda x: x.get("year", "0000"), reverse=True)
        else:
            mood_movies = sorted(mood_movies, key=lambda x: x.get("match", 0), reverse=True)
        mood_movies = mood_movies[:num_recommendations]
        col_m1, col_m2 = st.columns([2, 3])
        with col_m1:
            st.markdown(f"### 🌟 Mood Pick Recommendations")
        with col_m2:
            if total_mood_pages > 1:
                st.session_state.mood_page = st.selectbox(
                    "Select Page:", 
                    range(1, total_mood_pages + 1), 
                    index=st.session_state.mood_page - 1,
                    key="mood_page_selector"
                )

        COLS_PER_ROW = 5
        for row_start in range(0, len(mood_movies), COLS_PER_ROW):
            row_items = mood_movies[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)

            for idx, item in enumerate(row_items):
                with cols[idx]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                    if st.button(f"{item['title']} ({item['year']})", key=f"btn_mood_{item['movie_id']}_{row_start + idx}"):
                        show_movie_modal(item, prefix=f"mood_{row_start + idx}")



# --- Actors & Directors: independent people search and filmography page ---
elif main_tab_choice == "🎭 Actors & Directors":
    st.title("🎭 Actors & Directors")
    st.caption("Search performers and directors, explore their filmography, and open any movie for details.")
    st.subheader("Search Actor or Director Filmography")

    person_query = st.text_input("Search for actor or director:", key="person_search_input")

    # Clear the previous person's filmography as soon as the query changes.
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
            person_options = {
                f"{p.get('name')} ({p.get('known_for_department', 'Artist')} - Pop: {round(p.get('popularity', 0), 1)})": p
                for p in person_results
            }
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
                birth_line = f"**Born:** {person_details['birthday']}"
                if person_details.get("place_of_birth"):
                    birth_line += f" — {person_details['place_of_birth']}"
                st.markdown(birth_line)
            if person_details.get("deathday"):
                st.write(f"**Died:** {person_details['deathday']}")
            if person_details.get("known_for_department"):
                st.write(f"**Field:** {person_details.get('known_for_department')}")
            st.write(f"**TMDB popularity:** {round(person_details.get('popularity', selected_person.get('popularity', 0)) or 0, 1)}")
            known_for = selected_person.get("known_for", [])
            known_titles = [item.get("title") or item.get("name") for item in known_for if item.get("title") or item.get("name")]
            if known_titles:
                st.write("**Known for:** " + " · ".join(known_titles[:4]))
            biography = (person_details.get("biography") or "").strip()
            if biography:
                st.markdown("**Biography**")
                st.write(biography)
            else:
                st.info("TMDB has no biography for this person yet. Other profile details and filmography are shown when available.")
            homepage = person_details.get("homepage")
            if homepage:
                st.markdown(f"[Official website ↗]({homepage})")

    if selected_person_id:
        should_load_filmography = st.session_state.get("loaded_person_id") != selected_person_id
        if should_load_filmography or st.button("Show Full Filmography 🎥", type="primary", key="person_btn"):
            st.session_state.person_page = 1
            with st.spinner("Loading complete filmography..."):
                st.session_state.person_movies = get_person_filmography(selected_person_id)
                st.session_state.loaded_person_id = selected_person_id

    if (selected_person_id and st.session_state.get("loaded_person_id") == selected_person_id
            and st.session_state.get("person_movies")):
        st.markdown("---")
        all_p_movies = st.session_state.person_movies
        total_items = len(all_p_movies)
        items_per_page = 15
        total_p_pages = (total_items + items_per_page - 1) // items_per_page

        if "person_page" not in st.session_state:
            st.session_state.person_page = 1

        col_p1, col_p2 = st.columns([2, 3])
        with col_p1:
            st.markdown(f"### 🎬 Complete Works ({total_items} Movies)")
        with col_p2:
            if total_p_pages > 1:
                st.session_state.person_page = st.selectbox(
                    "Select Page:", 
                    range(1, total_p_pages + 1), 
                    index=st.session_state.person_page - 1,
                    key="person_page_selector"
                )

        start_idx = (st.session_state.person_page - 1) * items_per_page
        page_movies = all_p_movies[start_idx:start_idx + items_per_page]

        COLS_PER_ROW = 5
        for row_start in range(0, len(page_movies), COLS_PER_ROW):
            row_items = page_movies[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)

            for idx, item in enumerate(row_items):
                global_idx = start_idx + row_start + idx
                with cols[idx]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                    if st.button(f"{global_idx + 1}. {item['title']} ({item['year']})", key=f"btn_person_{item['movie_id']}_{global_idx}"):
                        show_movie_modal(item, prefix=f"person_{global_idx}")



# --- Movie Franchises: independent collections page ---
elif main_tab_choice == "🎞️ Movie Franchises":
    st.title("🎞️ Movie Franchises")
    st.caption("Browse popular franchises or search for any movie collection, then explore its films in order.")
    st.subheader("🔍 Explore Movie Franchises & Collections")
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
                    chosen_coll_name = st.selectbox("Select Collection from results:", coll_names, key="coll_selectbox")
                    selected_coll_id = coll_options.get(chosen_coll_name)
            else:
                st.info("No collections found for that search. Try a shorter or more general name.")

    if selected_coll_id:
        with st.spinner("Fetching full franchise chronologically..."):
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
                            st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                            if st.button(f"{idx + row_start + 1}. {item['title']} ({item['year']})", key=f"btn_coll_{item['movie_id']}_{row_start + idx}"):
                                show_movie_modal(item, prefix=f"coll_{row_start + idx}")


# --- TAB 3: My Watchlist ---
elif main_tab_choice == "❤️ My Watchlist":
    st.title(f"❤️ {user_name}'s Watchlist")
    st.caption("Track what you want to watch, what you have seen, and your own ratings.")
    if not is_logged_in:
        st.info("Guest Watchlist lasts for this browser session. Sign in to associate it with your account.")
    elif not supabase_storage_enabled():
        st.info("Cloud database is not configured. Your signed-in Watchlist currently uses local JSON storage, which may not persist on hosted deployments. See DATABASE_SETUP.md.")
    if not st.session_state.watchlist:
        st.info("Your Watchlist is empty. Open any movie and choose 'Add to Watchlist' to start your list.")
    else:
        statuses = ["All", "Want to Watch", "Watching", "Watched"]
        status_filter = st.selectbox("Filter by status", statuses, key="watchlist_status_filter")
        watchlist_items = [normalize_watchlist_item(m) for m in st.session_state.watchlist]
        if status_filter != "All":
            watchlist_items = [m for m in watchlist_items if m.get("status") == status_filter]
        st.markdown(f"**{len(watchlist_items)}** movies in this view · **{len(st.session_state.watchlist)}** saved in total")
        if not watchlist_items:
            st.info("No movies match this status yet.")
        COLS_PER_ROW = 5
        for row_start in range(0, len(watchlist_items), COLS_PER_ROW):
            row_items = watchlist_items[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(min(COLS_PER_ROW, len(row_items)))
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    st.image(item['poster'], use_container_width=True)
                    st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span> · {item["year"]}</div>', unsafe_allow_html=True)
                    if st.button(f"{item['title']}", key=f"btn_watch_{item['movie_id']}_{row_start + idx}", use_container_width=True):
                        show_movie_modal(item, prefix=f"watch_{row_start + idx}")
                    status_options = ["Want to Watch", "Watching", "Watched"]
                    new_status = st.selectbox("Status", status_options, index=status_options.index(item["status"]) if item["status"] in status_options else 0, key=f"wl_status_{item['movie_id']}")
                    new_rating = st.slider("Your rating", 0, 10, int(item.get("personal_rating", 0) or 0), key=f"wl_rating_{item['movie_id']}", help="0 means not rated yet")
                    new_note = st.text_input("Note (optional)", value=item.get("note", ""), key=f"wl_note_{item['movie_id']}", placeholder="Thoughts about this movie…")
                    if (new_status != item["status"] or new_rating != int(item.get("personal_rating", 0) or 0) or new_note != item.get("note", "")):
                        for saved in st.session_state.watchlist:
                            if saved.get("movie_id") == item.get("movie_id"):
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
