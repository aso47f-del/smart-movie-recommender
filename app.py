import streamlit as st
import requests
import random

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Smart Live Movie & Franchise Hub",
    page_icon="🎬",
    layout="wide"
)

# 2. تصميم CSS للبطاقات والتنسيق
st.markdown("""
    <style>
    div[data-testid="stImage"] img {
        border-radius: 12px;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    div[data-testid="stImage"] img:hover {
        transform: scale(1.03);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
    }
    .movie-title {
        font-weight: 700;
        font-size: 0.98rem;
        height: 2.8rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-top: 0.5rem;
        margin-bottom: 0.2rem;
    }
    .movie-info {
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .movie-rating { color: #ffb703; }
    .movie-match { color: #2ec4b6; }
    .cast-name {
        font-size: 0.8rem;
        text-align: center;
        font-weight: 600;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. إدارة مفتاح الـ API بأمان
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

@st.cache_data(show_spinner=False, ttl=86400)
def search_movie_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"Error searching movie: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_trending_movies():
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"Error fetching trending movies: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def search_collection_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/collection?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception as e:
        print(f"Error searching collection: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def search_person_tmdb(query):
    url = f"https://api.themoviedb.org/3/search/person?api_key={API_KEY}&query={query}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            results_sorted = sorted(results, key=lambda x: x.get("popularity", 0), reverse=True)
            return results_sorted
    except Exception as e:
        print(f"Error searching person: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_person_filmography(person_id):
    url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            cast_movies = data.get("cast", [])
            crew_movies = data.get("crew", [])
            
            all_movies_dict = {}
            for m in cast_movies + crew_movies:
                m_id = m.get("id")
                if m_id and m_id not in all_movies_dict:
                    all_movies_dict[m_id] = m
                    
            combined_movies = list(all_movies_dict.values())
            sorted_movies = sorted(combined_movies, key=lambda x: x.get("popularity", 0), reverse=True)
            
            formatted_movies = []
            for item in sorted_movies:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                rating = round(raw_rating, 1) if raw_rating else 0.0
                release_date = item.get("release_date", "N/A")[:4]
                
                formatted_movies.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': rating,
                    'year': release_date if release_date else "N/A"
                })
            return formatted_movies
    except Exception as e:
        print(f"Error fetching person filmography: {e}")
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
                rating = round(raw_rating, 1) if raw_rating else 0.0
                release_date = item.get("release_date", "N/A")[:4]
                
                movies.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': rating,
                    'year': release_date,
                    'match': int(item.get("popularity", 50)) % 15 + 80
                })
            return movies, total_pages
    except Exception as e:
        print(f"Error discovering movies: {e}")
    return [], 1

@st.cache_data(show_spinner=False, ttl=86400)
def get_collection_details(collection_id):
    url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            parts = data.get("parts", [])
            parts_sorted = sorted(parts, key=lambda x: x.get("release_date", "9999") or "9999")
            
            formatted_parts = []
            for item in parts_sorted:
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                rating = round(raw_rating, 1) if raw_rating else 0.0
                release_date = item.get("release_date", "N/A")[:4]
                
                formatted_parts.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': rating,
                    'year': release_date,
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
    except Exception as e:
        print(f"Error fetching collection details: {e}")
    return None

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_movie_modal_data(movie_id):
    info_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}&language=en-US"
    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}&language=en-US"
    
    overview = "No overview available."
    runtime = "N/A"
    imdb_id = None
    youtube_key = None
    director = "N/A"
    cast = []
    
    try:
        res_info = requests.get(info_url, timeout=5)
        if res_info.status_code == 200:
            data = res_info.json()
            overview = data.get("overview", "No overview available.")
            runtime = f"{data.get('runtime', 0)} mins"
            imdb_id = data.get("imdb_id")
            
        res_vid = requests.get(videos_url, timeout=5)
        if res_vid.status_code == 200:
            results = res_vid.json().get("results", [])
            for vid in results:
                if vid.get("site") == "YouTube" and vid.get("type") in ["Trailer", "Teaser"]:
                    youtube_key = vid.get("key")
                    break
                    
        res_credits = requests.get(credits_url, timeout=5)
        if res_credits.status_code == 200:
            c_data = res_credits.json()
            crew = c_data.get("crew", [])
            for person in crew:
                if person.get("job") == "Director":
                    director = person.get("name")
                    break
            cast = c_data.get("cast", [])[:4]
    except Exception as e:
        print(f"Error fetching modal details: {e}")
        
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
    except Exception as e:
        print(f"Error fetching watch providers: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=86400)
def get_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            poster_path = data.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
            raw_rating = data.get("vote_average", 0.0)
            rating = round(raw_rating, 1) if raw_rating else 0.0
            release_date = data.get("release_date", "N/A")[:4]
            return {
                'movie_id': data.get("id"),
                'title': data.get("title"),
                'poster': poster_url,
                'rating': rating,
                'year': release_date,
                'overview': data.get("overview", "")
            }
    except Exception as e:
        print(f"Error fetching selected movie details: {e}")
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
                genre_ids = item.get("genre_ids", [])
                if target_genre_id and target_genre_id not in genre_ids:
                    continue
                    
                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
                raw_rating = item.get("vote_average", 0.0)
                rating = round(raw_rating, 1) if raw_rating else 0.0
                release_date = item.get("release_date", "N/A")[:4]
                
                recommendations.append({
                    'movie_id': item.get("id"),
                    'title': item.get("title"),
                    'poster': poster_url,
                    'rating': rating,
                    'year': release_date,
                    'match': int(item.get("popularity", 50)) % 15 + 80
                })
            return recommendations
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
    return []

@st.dialog("🎬 Movie Details, Cast & Trailer", width="large")
def show_movie_modal(item):
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
                    if profile_path:
                        st.image(f"https://image.tmdb.org/t/p/w185{profile_path}", use_container_width=True)
                    else:
                        st.image(NO_IMAGE_URL, use_container_width=True)
                    st.markdown(f'<div class="cast-name">{actor.get("name")}</div>', unsafe_allow_html=True)
        
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

# الشريط الجانبي (Sidebar)
st.sidebar.header("⚙️ Controls & Filters")
num_recommendations = st.sidebar.slider("Number of Movies:", min_value=3, max_value=20, value=6, key="num_movies_slider")

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

st.sidebar.markdown("---")
if st.sidebar.button("Surprise Me! 🎲", use_container_width=True, key="surprise_btn"):
    trending = get_trending_movies()
    if trending:
        rand_movie = random.choice(trending)
        st.session_state.selected_movie_id = rand_movie.get("id")
        st.session_state.selected_movie_info = get_movie_details(rand_movie.get("id"))
        with st.spinner(f'Surprise! Recommending based on "{rand_movie.get("title")}"...'):
            st.session_state.recommendations = get_recommendations_from_tmdb(rand_movie.get("id"), selected_genre)

# الواجهة الرئيسية باستخدام 3 تبويبات (Tabs)
st.title("🎬 Smart Live Movie & Franchise Hub")
st.caption("Explore live recommendations, complete franchises, mood-based picks, and full actor/director filmographies!")

tab1, tab2, tab3 = st.tabs(["🍿 Recommendations", "🎞️ Franchises", "🎲 Mood & Cast Hub"])

# --- TAB 1: التوصيات العادية ---
with tab1:
    search_query = st.text_input("Search for any movie globally:", "Obsession", key="global_search_input")

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
        with st.spinner('Fetching movie details and live recommendations...'):
            st.session_state.selected_movie_info = get_movie_details(selected_movie_id)
            st.session_state.recommendations = get_recommendations_from_tmdb(selected_movie_id, selected_genre)

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
            if st.button("ℹ️ Full Details, Cast & Trailer", key="btn_selected_details"):
                show_movie_modal(sel_movie)

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
            st.warning(f"⚠️ No recommendations found matching the genre '{selected_genre}'.")
        else:
            COLS_PER_ROW = 5
            for row_start in range(0, len(results), COLS_PER_ROW):
                row_items = results[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                
                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-title">{item["title"]} ({item["year"]})</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="movie-info">'
                            f'<span class="movie-rating">⭐ {item["rating"]}/10</span> | '
                            f'<span class="movie-match">🎯 {item["match"]}%</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        
                        if st.button("ℹ️ Details", key=f"btn_{item['movie_id']}_{row_start + idx}"):
                            show_movie_modal(item)

# --- TAB 2: قسم سلاسل الأفلام (Franchises مع استخدام Radio لتجنب التداخل) ---
with tab2:
    st.subheader("🔍 Explore Movie Franchises & Collections")
    
    search_mode = st.radio(
        "Choose how to explore:", 
        ["Popular Franchises ⭐", "Search Any Franchise 🔍"], 
        horizontal=True,
        key="franchise_mode_radio"
    )
    
    selected_coll_id = None
    
    if search_mode == "Popular Franchises ⭐":
        preset_choice = st.selectbox(
            "Select a Popular Franchise:", 
            list(POPULAR_COLLECTIONS.keys()), 
            key="preset_franchise_sel"
        )
        selected_coll_id = POPULAR_COLLECTIONS.get(preset_choice)
    else:
        franchise_query = st.text_input(
            "Search for any Franchise / Collection (e.g., Batman, Star Wars):", 
            "", 
            key="franchise_search_input"
        )
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
                            st.markdown(f'<div class="movie-title">{idx + row_start + 1}. {item["title"]} ({item["year"]})</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-info"><span class="movie-rating">⭐ {item["rating"]}/10</span></div>', unsafe_allow_html=True)
                            
                            if st.button("ℹ️ Details", key=f"btn_coll_{item['movie_id']}_{row_start + idx}"):
                                show_movie_modal(item)

# --- TAB 3: موجه المزاج ومستكشف طاقم العمل (Mood & Cast Hub) ---
with tab3:
    sub_tab1, sub_tab2 = st.tabs(["🎲 Mood-Based Recommender", "🎭 Actor & Director Explorer"])
    
    # فرع 1: موجه المزاج مع نظام الصفحات
    with sub_tab1:
        st.subheader("How are you feeling today? Choose your mood:")
        selected_mood = st.selectbox("Select Mood:", list(MOOD_OPTIONS.keys()), key="mood_selector")
        
        if "mood_page" not in st.session_state:
            st.session_state.mood_page = 1
            
        if st.button("Find Movies 🎯", type="primary", key="mood_btn"):
            st.session_state.mood_page = 1
                
        mood_data = MOOD_OPTIONS[selected_mood]
        mood_movies, total_mood_pages = discover_movies_by_mood(mood_data["genres"], mood_data["sort"], page=st.session_state.mood_page)
        
        if mood_movies:
            st.markdown("---")
            st.markdown(f"### 🌟 Recommendations (Page {st.session_state.mood_page} of {total_mood_pages})")
            
            COLS_PER_ROW = 5
            for row_start in range(0, len(mood_movies), COLS_PER_ROW):
                row_items = mood_movies[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                
                for idx, item in enumerate(row_items):
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-title">{item["title"]} ({item["year"]})</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="movie-info">'
                            f'<span class="movie-rating">⭐ {item["rating"]}/10</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        if st.button("ℹ️ Details", key=f"btn_mood_{item['movie_id']}_{row_start + idx}"):
                            show_movie_modal(item)
                            
            st.markdown("")
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col1:
                if st.session_state.mood_page > 1:
                    if st.button("⬅️ Previous Page", key="mood_prev"):
                        st.session_state.mood_page -= 1
                        st.rerun()
            with p_col2:
                st.write(f"Page **{st.session_state.mood_page}** / {total_mood_pages}")
            with p_col3:
                if st.session_state.mood_page < total_mood_pages:
                    if st.button("Next Page ➡️", key="mood_next"):
                        st.session_state.mood_page += 1
                        st.rerun()

    # فرع 2: مستكشف الممثلين والمخرجين
    with sub_tab2:
        st.subheader("Explore Actor or Director Filmography")
        person_query = st.text_input("Search for an actor or director (e.g. Christopher Nolan, Leonardo DiCaprio):", "", key="person_search_input")
        
        selected_person_id = None
        if person_query:
            person_results = search_person_tmdb(person_query)
            if person_results:
                person_options = {}
                for p in person_results:
                    name = p.get('name', 'Unknown')
                    dept = p.get('known_for_department', 'Artist')
                    pop = round(p.get('popularity', 0), 1)
                    display_label = f"{name} ({dept} - Pop: {pop})"
                    person_options[display_label] = p.get('id')
                
                chosen_person = st.selectbox("Select Person:", list(person_options.keys()), key="person_selectbox")
                selected_person_id = person_options.get(chosen_person)
                
        if selected_person_id:
            if st.button("Show Full Filmography 🎥", type="primary", key="person_btn"):
                st.session_state.person_page = 1
                with st.spinner("Fetching complete filmography (Cast & Crew)..."):
                    st.session_state.person_movies = get_person_filmography(selected_person_id)
                    
        if "person_movies" in st.session_state and st.session_state.person_movies:
            st.markdown("---")
            all_p_movies = st.session_state.person_movies
            total_items = len(all_p_movies)
            items_per_page = 15
            total_p_pages = (total_items + items_per_page - 1) // items_per_page
            
            if "person_page" not in st.session_state:
                st.session_state.person_page = 1
                
            st.markdown(f"### 🎬 Complete Filmography (Total Works: {total_items}) - Page {st.session_state.person_page} of {total_p_pages}")
            
            start_idx = (st.session_state.person_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_movies = all_p_movies[start_idx:end_idx]
            
            COLS_PER_ROW = 5
            for row_start in range(0, len(page_movies), COLS_PER_ROW):
                row_items = page_movies[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                
                for idx, item in enumerate(row_items):
                    global_idx = start_idx + row_start + idx
                    with cols[idx]:
                        st.image(item['poster'], use_container_width=True)
                        st.markdown(f'<div class="movie-title">{global_idx + 1}. {item["title"]} ({item["year"]})</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="movie-info">'
                            f'<span class="movie-rating">⭐ {item["rating"]}/10</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        if st.button("ℹ️ Details", key=f"btn_person_{item['movie_id']}_{global_idx}"):
                            show_movie_modal(item)
                            
            if total_p_pages > 1:
                st.markdown("")
                pp_col1, pp_col2, pp_col3 = st.columns([1, 2, 1])
                with pp_col1:
                    if st.session_state.person_page > 1:
                        if st.button("⬅️ Previous Page", key="person_prev"):
                            st.session_state.person_page -= 1
                            st.rerun()
                with pp_col2:
                    st.write(f"Page **{st.session_state.person_page}** / {total_p_pages}")
                with pp_col3:
                    if st.session_state.person_page < total_p_pages:
                        if st.button("Next Page ➡️", key="person_next"):
                            st.session_state.person_page += 1
                            st.rerun()
