import streamlit as st
import pickle
import pandas as pd
import requests
import random
from concurrent.futures import ThreadPoolExecutor

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Smart Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# 2. تصميم CSS للمحاذاة والبطاقات
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

# 3. إدارة المفاتيح بأمان
try:
    API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    API_KEY = "9aeb1cb20dd00ae87552c5893e65b0a9"

NO_IMAGE_URL = "https://via.placeholder.com/500x750?text=No+Poster+Available"

ALL_GENRES = [
    "All", "Action", "Adventure", "Animation", "Comedy", "Crime", 
    "Documentary", "Drama", "Family", "Fantasy", "History", 
    "Horror", "Music", "Mystery", "Romance", "Science Fiction", 
    "TV Movie", "Thriller", "War", "Western"
]

@st.cache_data(show_spinner=False)
def fetch_movie_details(movie_id):
    """جلب بيانات الفيلم الأساسية من API"""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            raw_rating = data.get("vote_average", 0.0)
            release_date = data.get("release_date", "N/A")[:4]
            genres = [g['name'] for g in data.get("genres", [])]
            
            rating_val = round(raw_rating, 1) if raw_rating else 0.0
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else NO_IMAGE_URL
            
            return poster_url, rating_val, release_date, genres
    except Exception as e:
        print(f"Error fetching details for movie_id {movie_id}: {e}")
    
    return NO_IMAGE_URL, 0.0, "N/A", []

@st.cache_data(show_spinner=False)
def fetch_movie_modal_data(movie_id):
    """جلب تفاصيل القصة والتريلر ورابط IMDb للنافذة المنبثقة"""
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

@st.cache_data
def load_data():
    movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
    movies_df = pd.DataFrame(movies_dict)
    similarity_matrix = pickle.load(open('similarity.pkl', 'rb'))
    return movies_df, similarity_matrix

movies, similarity = load_data()

# 4. دالة النافذة المنبثقة (Modal Dialog)
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

def process_candidate(candidate_data, genre_filter, max_sim, min_sim):
    idx, sim_score = candidate_data
    movie_id = movies.iloc[idx].movie_id
    title = movies.iloc[idx].title
    
    poster, rating, release_year, genres = fetch_movie_details(movie_id)
    
    if genre_filter != "All":
        match_genre = genre_filter.lower()
        genres_lower = [g.lower() for g in genres]
        if match_genre == "sci-fi":
            match_genre = "science fiction"
        if match_genre not in genres_lower:
            return None

    normalized_rating = rating / 10.0
    
    if max_sim > min_sim:
        match_percentage = int(70 + ((sim_score - min_sim) / (max_sim - min_sim)) * 28)
    else:
        match_percentage = 85

    hybrid_score = ((match_percentage / 100.0) * 0.5) + (normalized_rating * 0.5)

    return {
        'movie_id': movie_id,
        'title': title,
        'poster': poster,
        'rating': rating,
        'year': release_year,
        'similarity': sim_score,
        'match': match_percentage,
        'hybrid_score': hybrid_score
    }

def recommend(movie_name, top_n=6, genre_filter="All", sort_by="Similarity & Rating (Hybrid)"):
    movie_index = movies[movies['title'] == movie_name].index[0]
    distances = similarity[movie_index]
    
    movie_candidates = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:151]
    
    max_sim = max([cand[1] for cand in movie_candidates]) if movie_candidates else 1.0
    min_sim = min([cand[1] for cand in movie_candidates]) if movie_candidates else 0.0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_candidate, cand, genre_filter, max_sim, min_sim) 
            for cand in movie_candidates
        ]
        recommendations = [f.result() for f in futures if f.result() is not None]

    if sort_by == "Highest Rating":
        recommendations = sorted(recommendations, key=lambda x: x['rating'], reverse=True)
    elif sort_by == "Pure Similarity":
        recommendations = sorted(recommendations, key=lambda x: x['similarity'], reverse=True)
    elif sort_by == "Release Year (Newest)":
        recommendations = sorted(recommendations, key=lambda x: x['year'], reverse=True)
    else:
        recommendations = sorted(recommendations, key=lambda x: x['hybrid_score'], reverse=True)

    return recommendations[:top_n]

# 5. الشريط الجانبي (Sidebar)
st.sidebar.header("⚙️ Controls & Filters")

# زيادة الحد الأقصى لـ 20 فيلم
num_recommendations = st.sidebar.slider("Number of Movies:", min_value=3, max_value=20, value=6)

sort_option = st.sidebar.selectbox(
    "Sort Recommendations By:",
    [
        "Similarity & Rating (Hybrid)", 
        "Highest Rating", 
        "Pure Similarity", 
        "Release Year (Newest)"
    ]
)

selected_genre = st.sidebar.selectbox(
    "Filter by Genre:",
    ALL_GENRES
)

# زر المفاجأة مع تصفية جودة الأفلام
st.sidebar.markdown("---")
if st.sidebar.button("Surprise Me! 🎲", use_container_width=True):
    # اختيار عشوائي لفيلم ذو تقييم جيد إن أمكن، وإلا اختيار من القائمة العامة
    random_movie = random.choice(movies['title'].values)
    st.session_state.selected_movie = random_movie
    
    with st.spinner(f'Surprise! Recommending based on "{random_movie}"...'):
        st.session_state.recommendations = recommend(
            random_movie, 
            top_n=num_recommendations, 
            genre_filter=selected_genre, 
            sort_by=sort_option
        )

# 6. الواجهة الرئيسية
st.title("🎬 Smart Movie Recommender System")
st.caption("Select a movie, choose genres like Horror or Action, and get balanced recommendations!")

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = movies['title'].values[0]

selected_movie_name = st.selectbox(
    "Search for or select a movie:",
    movies['title'].values,
    index=int(movies[movies['title'] == st.session_state.selected_movie].index[0]) if st.session_state.selected_movie in movies['title'].values else 0
)

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if st.button("Get Recommendations 🚀", type="primary"):
    st.session_state.selected_movie = selected_movie_name
    with st.spinner('Fetching best matches from database...'):
        st.session_state.recommendations = recommend(
            selected_movie_name, 
            top_n=num_recommendations, 
            genre_filter=selected_genre, 
            sort_by=sort_option
        )

# عرض النتائج في شبكة متناسقة (5 أفلام في كل سطر)
if st.session_state.recommendations:
    results = st.session_state.recommendations
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