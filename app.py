import streamlit as st
import requests

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Smart Live Movie Recommender",
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
def fetch_movie_modal_data(movie_id):
    info_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}&language=en-US"
    
    overview = "No overview available."
    runtime = "N/A"
    imdb_id = None
    youtube_key = None
    
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
    except Exception as e:
        print(f"Error fetching modal details: {e}")
        
    return overview, runtime, imdb_id, youtube_key

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

@st.dialog("🎬 Movie Details & Trailer", width="large")
def show_movie_modal(item):
    overview, runtime, imdb_id, youtube_key = fetch_movie_modal_data(item['movie_id'])
    
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
        st.markdown("**Overview / Storyline:**")
        st.write(overview)
        
        if youtube_key:
            st.markdown("**Official Trailer:**")
            st.video(f"https://www.youtube.com/watch?v={youtube_key}")
        else:
            st.info("No trailer video available for this movie.")

# الشريط الجانبي
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
        import random
        rand_movie = random.choice(trending)
        st.session_state.selected_movie_id = rand_movie.get("id")
        st.session_state.selected_movie_info = get_movie_details(rand_movie.get("id"))
        with st.spinner(f'Surprise! Recommending based on "{rand_movie.get("title")}"...'):
            st.session_state.recommendations = get_recommendations_from_tmdb(rand_movie.get("id"), selected_genre)

# الواجهة الرئيسية
st.title("🎬 Smart Live Movie Recommender System")
st.caption("Now powered by live TMDB API — updated daily with new releases and no CSV files required!")

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

# 1. عرض الفيلم المختار في قسم منفصل بالأعلى
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
        if st.button("ℹ️ Full Details & Trailer", key="btn_selected_details"):
            show_movie_modal(sel_movie)

    st.markdown("---")
    st.subheader("🍿 Recommended Movies")

# 2. عرض نتائج التوصيات أسفله
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
        st.warning(f"⚠️ No recommendations found matching the genre '{selected_genre}' for this movie. Try choosing 'All' or a different genre!")
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
elif "selected_movie_info" not in st.session_state:
    st.info("Search for a movie and click 'Get Recommendations' to start exploring!")
