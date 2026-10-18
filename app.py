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

# 2. CSS Styling for IMDb Header & Modern Clean UI
st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
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

# Helper Functions for Persistent Watchlist per User Email
def get_watchlist_filename(email):
    safe_email = "".join([c if c.isalnum() else "_" for c in email])
    return f"watchlist_{safe_email}.json"

def load_user_watchlist(email):
    filename = get_watchlist_filename(email)
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_user_watchlist(email, watchlist):
    filename = get_watchlist_filename(email)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# Determine Authenticated User Info
if st.user.is_logged_in:
    user_email = st.user.get("email", "user@gmail.com")
    user_name = st.user.get("name", "Movie Fan")
else:
    user_email = "guest_user@gmail.com"
    user_name = "Guest"

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
    "Mission: Impossible Collection": 87096,
    "The Avengers Collection": 86311,
    "The Godfather Collection": 230,
    "Toy Story Collection": 10194
}

MOOD_OPTIONS = {
    "Action & Adventure 🏃‍♂️": {"genres": "28,12", "sort": "popularity.desc"},
    "Mystery & Thriller 🕵️‍♂️": {"genres": "9648,53", "sort": "vote_average.desc"},
    "Family & Animation 🍿": {"genres": "10751,16", "sort": "popularity.desc"},
    "Horror 👻": {"genres": "27", "sort": "popularity.desc"},
    "Romance & Drama 💖": {"genres": "10749,18", "sort": "vote_average.desc"}
}

# --- API Functions with Optimized Caching TTL ---

@st.cache_data(show_spinner=False, ttl=86400)
def search_movie_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_trending_movies():
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
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
                    'year': item.get("release_date", "N/A")[:4]
                })
            return movies
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_movies_by_genre(genre_id):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
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
                    'year': item.get("release_date", "N/A")[:4]
                })
            return movies
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
        pass
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def discover_movies_by_mood(genre_ids, sort_by, page=1):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_ids}&sort_by={sort_by}&page={page}&language=en-US"
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
        pass
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
        pass
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
        pass
    return overview, runtime, imdb_id, youtube_key, director, cast

@st.cache_data(show_spinner=False, ttl=86400)
def get_movie_watch_providers(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get("results", {})
            for country in ['US', 'EG', 'GB', 'FR']:
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
        pass
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
        pass
    return []

# --- Movie Details Modal Dialog ---
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
            st.session_state.watchlist = load_user_watchlist(user_email)
        
        is_in_watchlist = any(m['movie_id'] == item['movie_id'] for m in st.session_state.watchlist)
        if not is_in_watchlist:
            if st.button("❤️ Add to Watchlist", key=f"{prefix}_add_{item['movie_id']}"):
                st.session_state.watchlist.append(item)
                save_user_watchlist(user_email, st.session_state.watchlist)
                st.toast("Added to watchlist! ❤️", icon="✅")
                st.rerun()
        else:
            if st.button("❌ Remove from Watchlist", key=f"{prefix}_rem_{item['movie_id']}"):
                st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                save_user_watchlist(user_email, st.session_state.watchlist)
                st.toast("Removed from watchlist.", icon="🗑️")
                st.rerun()
        
    with col2:
        st.subheader(f"{item['title']} ({item['year']})")
        st.markdown(f"🎬 **Director:** {director}")
        st.markdown("**Overview / Storyline:**")
        st.write(overview)
        
        if cast:
            st.markdown("**👥 Top Cast:**")
            cast_cols = st.columns(len(cast))
            for i, actor in enumerate(cast):
                with cast_cols[i]:
                    profile_path = actor.get("profile_path")
                    img_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else NO_IMAGE_URL
                    st.image(img_url, use_container_width=True)
                    if st.button(f"👤 {actor.get('name')}", key=f"{prefix}_actor_{actor.get('id')}_{i}"):
                        st.session_state.menu_choice = "🔍 Global Search & Franchises"
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

# ==============================================================================
# --- IMDb Style Top Navigation Bar ---
# ==============================================================================
if "menu_choice" not in st.session_state:
    st.session_state.menu_choice = "🏠 Home"

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_user_watchlist(user_email)

col_logo, col_menu, col_search, col_watchlist, col_auth = st.columns([1.2, 2.2, 3, 1.3, 1.3])

with col_logo:
    st.markdown("### 🎬 IMDb Hub")

with col_menu:
    st.session_state.menu_choice = st.selectbox(
        "Menu",
        [
            "🏠 Home", 
            "🍿 Discover & Recommendations", 
            "🔍 Global Search & Franchises", 
            "❤️ My Watchlist"
        ],
        index=[
            "🏠 Home", 
            "🍿 Discover & Recommendations", 
            "🔍 Global Search & Franchises", 
            "❤️ My Watchlist"
        ].index(st.session_state.menu_choice) if st.session_state.menu_choice in [
            "🏠 Home", "🍿 Discover & Recommendations", "🔍 Global Search & Franchises", "❤️ My Watchlist"
        ] else 0,
        key="menu_selectbox",
        label_visibility="collapsed"
    )

with col_search:
    top_search_query = st.text_input("Search IMDb...", placeholder="Search any movie...", key="top_search_input", label_visibility="collapsed")

with col_watchlist:
    if st.button(f"❤️ Watchlist ({len(st.session_state.watchlist)})", use_container_width=True):
        st.session_state.menu_choice = "❤️ My Watchlist"
        st.rerun()

with col_auth:
    if st.user.is_logged_in:
        if st.button("Sign Out 🚪", use_container_width=True):
            st.logout()
    else:
        if st.button("Sign In 🔑", use_container_width=True):
            st.login("google")

st.markdown("---")

# If the user performed a top search, handle search view cleanly
if top_search_query:
    st.title(f"🔍 Search Results for: '{top_search_query}'")
    search_results = search_movie_tmdb(top_search_query)
    if search_results:
        COLS_PER_ROW = 5
        for row_start in range(0, min(len(search_results), 15), COLS_PER_ROW):
            row_items = search_results[row_start : row_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    poster_path = item.get("poster_path")
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                    raw_rating = item.get("vote_average", 0.0)
                    movie_obj = {
                        'movie_id': item.get("id"),
                        'title': item.get("title"),
                        'poster': poster_url,
                        'rating': round(raw_rating, 1) if raw_rating else 0.0,
                        'year': item.get("release_date", "N/A")[:4]
                    }
                    st.image(poster_url, use_container_width=True)
                    st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {movie_obj["rating"]}/10</span></div>', unsafe_allow_html=True)
                    if st.button(f"{movie_obj['title']} ({movie_obj['year']})", key=f"top_search_{movie_obj['movie_id']}_{idx}"):
                        show_movie_modal(movie_obj, prefix=f"top_search_{idx}")
    else:
        st.info("No movies found matching your query.")
    st.markdown("---")
    st.stop()  # Stop rendering Home so search results take full focus cleanly

# ==============================================================================
# --- MAIN PAGES ROUTING ---
# ==============================================================================

current_tab = st.session_state.menu_choice

# --- 1. HOME PAGE ---
if current_tab == "🏠 Home":
    st.title("🎬 Welcome to Movie & Franchise Hub")
    st.caption(f"Hello, {user_name}! Explore trending movies and categorized collections below.")
    
    # Initialize pagination offsets in session state if not present
    if "offsets" not in st.session_state:
        st.session_state.offsets = {}

    def render_row_with_arrows(section_key, movies_list):
        if not movies_list:
            return
        
        if section_key not in st.session_state.offsets:
            st.session_state.offsets[section_key] = 0
            
        current_offset = st.session_state.offsets[section_key]
        items_per_page = 5
        max_start = max(0, len(movies_list) - items_per_page)
        
        # Header with Arrows '<' and '>'
        col_title, col_btn1, col_btn2 = st.columns([10, 1, 1])
        with col_title:
            st.subheader(section_key)
        with col_btn1:
            if st.button("◀", key=f"prev_{section_key}"):
                if st.session_state.offsets[section_key] >= items_per_page:
                    st.session_state.offsets[section_key] -= items_per_page
                else:
                    st.session_state.offsets[section_key] = max_start
                st.rerun()
        with col_btn2:
            if st.button("▶", key=f"next_{section_key}"):
                if st.session_state.offsets[section_key] + items_per_page < len(movies_list):
                    st.session_state.offsets[section_key] += items_per_page
                else:
                    st.session_state.offsets[section_key] = 0
                st.rerun()
                
        visible_movies = movies_list[current_offset : current_offset + items_per_page]
        cols = st.columns(5)
        for idx, item in enumerate(visible_movies):
            with cols[idx]:
                st.image(item['poster'], use_container_width=True)
                st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                if st.button(f"{item['title']} ({item['year']})", key=f"row_{section_key}_{item['movie_id']}_{current_offset + idx}"):
                    show_movie_modal(item, prefix=f"row_{section_key}_{idx}")
        st.markdown("---")

    # Trending Section
    trending_movies = get_trending_movies()
    render_row_with_arrows("🔥 Trending Today", trending_movies)

    # Categories Sections (English Only)
    categories = [
        {"name": "👻 Horror Movies", "id": 27},
        {"name": "🏃‍♂️ Action Movies", "id": 28},
        {"name": "😂 Comedy Movies", "id": 35},
        {"name": "🍿 Animation & Cartoons", "id": 16},
        {"name": "🎭 Drama Movies", "id": 18},
        {"name": "🚀 Science Fiction", "id": 878}
    ]

    for cat in categories:
        cat_movies = get_movies_by_genre(cat["id"])
        render_row_with_arrows(cat["name"], cat_movies)

# --- 2. DISCOVER & RECOMMENDATIONS ---
elif current_tab == "🍿 Discover & Recommendations":
    st.title("🍿 Discover & Recommendations")
    sub_tab1, sub_tab2 = st.tabs(["🚀 Movie-based Recommendations", "🎲 Mood-based Discovery"])
    
    with sub_tab1:
        search_query = st.text_input("Search movie to get tailored recommendations:", "Interstellar", key="rec_search_input")
        selected_movie_id = None
        if search_query:
            search_results = search_movie_tmdb(search_query)
            if search_results:
                movie_options = {f"{m.get('title')} ({m.get('release_date', 'N/A')[:4]})": m.get("id") for m in search_results}
                chosen_option = st.selectbox("Select from search results:", list(movie_options.keys()), key="rec_selectbox")
                selected_movie_id = movie_options.get(chosen_option)

        if "recommendations" not in st.session_state:
            st.session_state.recommendations = []

        genre_filter = st.selectbox("Filter Recommendations by Genre:", ALL_GENRES, key="disc_genre_sel")
        num_recs = st.slider("Number of Recommendations:", 3, 20, 5, key="disc_slider")

        if st.button("Get Recommendations 🚀", type="primary") and selected_movie_id:
            with st.spinner("Fetching recommendations..."):
                st.session_state.selected_movie_info = get_movie_details(selected_movie_id)
                st.session_state.recommendations = get_recommendations_from_tmdb(selected_movie_id, genre_filter)

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
                if st.button(f"🎬 View Details: {sel_movie['title']}", key="btn_sel_modal"):
                    show_movie_modal(sel_movie, prefix="sel_modal")

            st.markdown("---")
            st.subheader("🍿 Recommended Movies")

        if st.session_state.recommendations:
            recs = st.session_state.recommendations[:num_recs]
            COLS_PER_ROW = 5
            for row_start in range(0, len(recs), COLS_PER_ROW):
                row_items = recs[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                        if st.button(f"{item['title']} ({item['year']})", key=f"recs_item_{item['movie_id']}_{row_start + idx}"):
                            show_movie_modal(item, prefix=f"recs_item_{row_start + idx}")

    with sub_tab2:
        st.subheader("🎲 Mood-Based Movie Finder")
        selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()), key="mood_selector")
        mood_data = MOOD_OPTIONS[selected_mood]
        
        if "mood_page" not in st.session_state:
            st.session_state.mood_page = 1
            
        if st.button("Find Movies by Mood 🎯", type="primary"):
            st.session_state.mood_page = 1
