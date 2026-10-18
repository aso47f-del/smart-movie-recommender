import streamlit as st
import requests
import random
import time

# 1. Page Configuration
st.set_page_config(
    page_title="Smart Live Movie & Franchise Hub",
    page_icon="🎬",
    layout="wide"
)

# 2. CSS Styling for IMDb/Netflix Style Horizontal Touch Scroll & Clean UI
st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }

    /* تحويل أعمدة Streamlit لشريط سحب أفقي ناعم على الموبايل زي IMDb */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            gap: 10px !important;
            padding-bottom: 10px !important;
            scroll-snap-type: x mandatory !important;
            -webkit-overflow-scrolling: touch !important;
        }
        div[data-testid="column"] {
            flex: 0 0 140px !important;
            min-width: 140px !important;
            max-width: 140px !important;
            scroll-snap-align: start !important;
            background: #1a1a24 !important;
            border-radius: 10px !important;
            padding: 6px !important;
            border: 1px solid #2a2a3a !important;
        }
        div[data-testid="stImage"] img {
            height: 190px !important;
            object-fit: cover !important;
            border-radius: 6px !important;
        }
        div.stButton > button {
            font-size: 0.7rem !important;
            height: 2.2rem !important;
            padding: 0px 2px !important;
        }
    }

    .movie-info {
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        margin-top: 4px;
    }
    .movie-rating { color: #f5c518; }
    .movie-match { color: #2ec4b6; }
    </style>
""", unsafe_allow_html=True)

# 3. Secure API Key Management
try:
    API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    st.error("Please configure TMDB_API_KEY in Streamlit secrets.")
    st.stop()

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

# --- API Functions ---

@st.cache_data(show_spinner=False, ttl=86400)
def search_movie_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        st.toast(f"⚠️ Connection error: {e}", icon="🚨")
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
            cast = c_data.get("cast", [])[:6]
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

# --- Movie Details Modal ---
@st.dialog("🎬 Movie Details, Cast & Trailer", width="large")
def show_movie_modal(item, prefix="modal"):
    overview, runtime, imdb_id, youtube_key, director, cast = fetch_movie_modal_data(item['movie_id'])
    providers = get_movie_watch_providers(item['movie_id'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(item['poster'], use_container_width=True)
        st.markdown(f"**Year:** {item['year']} | **Runtime:** {runtime}")
        st.markdown(f"**Rating:** ⭐ {item['rating']}/10")
        if imdb_id:
            st.markdown(f"[🔗 Open in IMDb](https://www.imdb.com/title/{imdb_id})")
        
        if "watchlist" not in st.session_state:
            st.session_state.watchlist = []
        
        is_in_watchlist = any(m['movie_id'] == item['movie_id'] for m in st.session_state.watchlist)
        if not is_in_watchlist:
            if st.button("❤️ Add to Watchlist", key=f"{prefix}_add_{item['movie_id']}"):
                st.session_state.watchlist.append(item)
                st.toast("Added to watchlist! ❤️", icon="✅")
                st.rerun()
        else:
            if st.button("❌ Remove from Watchlist", key=f"{prefix}_rem_{item['movie_id']}"):
                st.session_state.watchlist = [m for m in st.session_state.watchlist if m['movie_id'] != item['movie_id']]
                st.toast("Removed from watchlist.", icon="🗑️")
                st.rerun()
        
    with col2:
        st.subheader(f"{item['title']} ({item['year']})")
        st.markdown(f"🎬 **Director:** {director}")
        st.markdown("**Storyline:**")
        st.write(overview)
        
        # IMDb-Style Cast Horizontal Carousel
        if cast:
            st.markdown("**👥 Top Cast:**")
            cast_cols = st.columns(len(cast))
            for i, actor in enumerate(cast):
                with cast_cols[i]:
                    profile_path = actor.get("profile_path")
                    img_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else NO_IMAGE_URL
                    st.image(img_url, use_container_width=True)
                    if st.button(f"{actor.get('name')}", key=f"{prefix}_actor_{actor.get('id')}_{i}"):
                        st.session_state.main_nav_tab = "🔍 Global Search Hub"
                        st.session_state.person_search_input = actor.get('name')
                        st.rerun()
        
        st.markdown("**📺 Where to Watch:**")
        if providers:
            prov_cols = st.columns(min(len(providers), 4))
            for i, prov in enumerate(providers[:4]):
                with prov_cols[i]:
                    logo_path = prov.get("logo_path")
                    if logo_path:
                        st.image(f"https://image.tmdb.org/t/p/w92{logo_path}", width=40)
                    st.caption(prov.get("provider_name"))
        else:
            st.info("No streaming providers available.")
        
        if youtube_key:
            st.markdown("**Official Trailer:**")
            st.video(f"https://www.youtube.com/watch?v={youtube_key}")

# Sidebar Controls & Filters
st.sidebar.header("⚙️ Controls & Filters")
num_recommendations = st.sidebar.slider("Number of Movies:", min_value=4, max_value=20, value=10, key="num_movies_slider")

sort_option = st.sidebar.selectbox(
    "Sort Recommendations By:",
    ["Popularity / Match", "Highest Rating", "Release Year (Newest)"],
    key="sort_option_select"
)

selected_genre = st.sidebar.selectbox(
    "Filter by Genre:",
    ALL_GENRES,
    key="genre_filter_select"
)

# Main UI Title & Navigation Hub
st.title("🎬 Smart Live Movie & Franchise Hub")

if "main_nav_tab" not in st.session_state:
    st.session_state.main_nav_tab = "🍿 Discover & Recommendations"

main_tab_choice = st.radio(
    "Navigation Hub",
    ["🍿 Discover & Recommendations", "🔍 Global Search Hub", "❤️ My Watchlist"],
    horizontal=True,
    key="main_nav_tab",
    label_visibility="collapsed"
)

st.markdown("---")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# --- Render Horizontal Movie Carousel (IMDb / Netflix Style) ---
def render_movie_carousel(movies_list, prefix_key):
    cols = st.columns(len(movies_list))
    for idx, item in enumerate(movies_list):
        with cols[idx]:
            st.image(item['poster'], use_container_width=True)
            match_str = f' | <span class="movie-match">🎯 {item["match"]}%</span>' if 'match' in item else ''
            st.markdown(
                f'<div class="movie-info">'
                f'<span class="movie-rating">⭐ {item["rating"]}</span>{match_str}'
                f'</div>', 
                unsafe_allow_html=True
            )
            if st.button(f"{item['title']}", key=f"{prefix_key}_{item['movie_id']}_{idx}"):
                show_movie_modal(item, prefix=f"{prefix_key}_{idx}")

# --- TAB 1: Discover & Recommendations ---
if main_tab_choice == "🍿 Discover & Recommendations":
    sub_tab1, sub_tab2 = st.tabs(["🚀 Movie-based Recommendations", "🎲 Mood-based Discovery"])
    
    with sub_tab1:
        search_query = st.text_input("Search movie to get tailored recommendations:", "Obsession", key="global_search_input")

        selected_movie_id = None
        if search_query:
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

        if st.button("Get Recommendations 🚀", type="primary", key="get_recs_btn") and selected_movie_id:
            with st.spinner("Fetching live movie recommendations..."):
                st.session_state.selected_movie_info = get_movie_details(selected_movie_id)
                st.session_state.recommendations = get_recommendations_from_tmdb(selected_movie_id, selected_genre)

        # 1. Selected Movie Header (IMDb Style)
        if "selected_movie_info" in st.session_state and st.session_state.selected_movie_info:
            sel_movie = st.session_state.selected_movie_info
            st.markdown("---")
            st.subheader("🎯 Selected Movie")
            
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(sel_movie['poster'], use_container_width=True)
            with col_info:
                st.markdown(f"## {sel_movie['title']} ({sel_movie['year']})")
                st.markdown(f"⭐ **IMDb Rating:** {sel_movie['rating']}/10")
                st.write(sel_movie['overview'])
                if st.button(f"🎬 Play Trailer & Details", key="btn_selected_details", type="primary"):
                    show_movie_modal(sel_movie, prefix="selected")

            st.markdown("---")
            st.subheader("🍿 Recommended Movies (Swipe Left/Right 👈👉)")

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
                render_movie_carousel(results, "recs")

    with sub_tab2:
        st.subheader("🎲 Mood-Based Movie Finder")
        selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()), key="mood_selector")
        
        if "mood_page" not in st.session_state:
            st.session_state.mood_page = 1
            
        if st.button("Find Movies by Mood 🎯", type="primary", key="mood_btn"):
            st.session_state.mood_page = 1
                
        mood_data = MOOD_OPTIONS[selected_mood]
        
        with st.spinner("Finding movies matching your mood..."):
            mood_movies, total_mood_pages = discover_movies_by_mood(mood_data["genres"], mood_data["sort"], page=st.session_state.mood_page)
        
        if mood_movies:
            st.markdown("### 🌟 Mood Picks (Swipe 👈👉)")
            render_movie_carousel(mood_movies, "mood")

# --- TAB 2: Global Search Hub ---
elif main_tab_choice == "🔍 Global Search Hub":
    search_sub_tab1, search_sub_tab2 = st.tabs(["Actor & Director Explorer", "Franchises & Collections"])
    
    with search_sub_tab1:
        st.subheader("Search Actor or Director Filmography")
        person_query = st.text_input("Search for actor or director:", key="person_search_input")
        
        selected_person_id = None
        if person_query:
            person_results = search_person_tmdb(person_query)
            if person_results:
                person_options = {f"{p.get('name')} ({p.get('known_for_department', 'Artist')} - Pop: {round(p.get('popularity', 0), 1)})": p.get('id') for p in person_results}
                chosen_person = st.selectbox("Select Person:", list(person_options.keys()), key="person_selectbox")
                selected_person_id = person_options.get(chosen_person)
                
        if selected_person_id:
            if st.button("Show Full Filmography 🎥", type="primary", key="person_btn") or person_query:
                with st.spinner("Loading complete filmography..."):
                    st.session_state.person_movies = get_person_filmography(selected_person_id)
                    
        if "person_movies" in st.session_state and st.session_state.person_movies:
            st.markdown("---")
            st.markdown(f"### 🎬 Complete Works ({len(st.session_state.person_movies)} Movies)")
            render_movie_carousel(st.session_state.person_movies[:15], "person")

    with search_sub_tab2:
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
                    coll_options = {c.get("name"): c.get("id") for c in coll_results}
                    chosen_coll_name = st.selectbox("Select Collection from results:", list(coll_options.keys()), key="coll_selectbox")
                    selected_coll_id = coll_options.get(chosen_coll_name)

        if selected_coll_id:
            with st.spinner("Fetching full franchise chronologically..."):
                collection = get_collection_details(selected_coll_id)
                if collection:
                    st.markdown("---")
                    st.markdown(f"## {collection['name']}")
                    st.write(collection['overview'])
                    st.markdown("### 🎬 Movies in Chronological Order (Swipe 👈👉):")
                    render_movie_carousel(collection['parts'], "coll")

# --- TAB 3: My Watchlist ---
elif main_tab_choice == "❤️ My Watchlist":
    st.subheader("❤️ Your Personal Watchlist")
    if not st.session_state.watchlist:
        st.info("Your watchlist is currently empty.")
    else:
        render_movie_carousel(st.session_state.watchlist, "watch")
        st.markdown("---")
        if st.button("🗑️ Clear Entire Watchlist", type="secondary"):
            st.session_state.watchlist = []
            st.toast("Watchlist cleared successfully.", icon="🧹")
            st.rerun()
