import streamlit as st
from datetime import datetime, timedelta
from textblob import TextBlob
import emoji
import pandas as pd
import math
from pathlib import Path

# Initialize session state for storing posts
if 'posts' not in st.session_state:
    st.session_state.posts = []
    
    # Load from CSV (works both locally and in deployment)
    try:
        # For deployment, we'll package the CSV with the app
        csv_path = Path(__file__).parent / "sample_posts.csv"
        sample_df = pd.read_csv(csv_path, parse_dates=['created_at'])
        
        # Convert to list of dictionaries
        sample_posts = sample_df.to_dict('records')
        
        # Ensure datetime format
        for post in sample_posts:
            if isinstance(post['created_at'], str):
                post['created_at'] = datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                
        st.session_state.posts = sample_posts
    
    except Exception as e:
        st.warning(f"Couldn't load sample posts: {e}")
        # Fallback to hardcoded samples     
    
    
        # Pre-load sample posts
        sample_posts = [
            {
                "text": "KGF 2 is paisa vasool! Best action in Indian cinema 🔥",
                "likes": 21,
                "comments": 6,
                "author_content_watched": 123,
                "author_reviews_posted": 111,
                "author_public_watchlists": 2,
                "media_count": 2,
                "created_at": datetime.now() - timedelta(hours=72)
            },
            {
                "text": "Pathaan was timepass but too much drama 😒",
                "likes": 9,
                "comments": 2,
                "author_content_watched": 234,
                "author_reviews_posted": 189,
                "author_public_watchlists": 3,
                "media_count": 1,
                "created_at": datetime.now() - timedelta(hours=62)
            },
            {
                "text": "RRR deserves all the international awards 👏👌",
                "likes": 17,
                "comments":3,
                "author_content_watched": 321,
                "author_reviews_posted": 313,
                "author_public_watchlists": 5,
                "media_count": 3,
                "created_at": datetime.now() - timedelta(hours=12)
            },
            {
                "text": "Just watched Avatar 2 - visuals are mind-blowing but story is weak 🤷‍♂️",
                "likes": 8,
                "comments": 1,
                "author_content_watched": 79,
                "author_reviews_posted": 77,
                "author_public_watchlists": 2,
                "media_count": 0,
                "created_at": datetime.now() - timedelta(hours=42)
            }
        ]
        
        st.session_state.posts = sample_posts

# Scoring functions
def calculate_emoji_sentiment(text):
    """Calculate sentiment from emojis (returns value between -0.5 to +0.5)"""
    emoji_sentiment_map = {
        # Positive emojis
        '❤️': 0.3, '👌': 0.3, '👍': 0.2, '😍': 0.3, '🔥': 0.2,
        '🎉': 0.2, '🤩': 0.3, '🙌': 0.2, '💯': 0.3, '😊': 0.2,
        # Negative emojis
        '👎': -0.3, '😒': -0.2, '💔': -0.3, '😠': -0.3, '🤮': -0.4,
        '😤': -0.2, '😑': -0.1, '🙄': -0.2
    }
    
    total_score = 0
    emojis = [c for c in text if c in emoji.EMOJI_DATA]
    
    for e in emojis:
        total_score += emoji_sentiment_map.get(e, 0)
    
    # Normalize to prevent overpowering
    return max(-0.5, min(0.5, total_score))

def check_movie_relevance(text):
    """Enhanced Hinglish movie detection (returns score 0-1)"""
    # English movie terms
    english_terms = [
        "movie", "film", "cinema", "bollywood", "hollywood",
        "watch", "review", "actor", "actress", "director",
        "scene", "ending", "plot", "story", "screenplay"
    ]
    
    
    # Common Hinglish phrases about movies
    hinglish_phrases = [
        "paisa vasool", "time pass", "mind blowing",
        "must watch", "mat dekho", "bakwas movie",
        "hit hai", "flop hai", "time waste"
    ]
    
    text_lower = text.lower()
    
    # Check for exact matches
    term_matches = (
        sum(1 for term in english_terms if term in text_lower) +
        sum(1 for phrase in hinglish_phrases if phrase in text_lower)
    )
    
    # Return score based on number of matches (0.2 base score if no matches)
    return min(1.0, 0.2 + (term_matches * 0.15))

def calculate_post_score(post):
    """
    Calculate a score (0-100) for ranking posts.
    """
    # Dynamic normalization values (should come from config)
    LIKE_NORM = 250
    COMMENT_NORM = 30
    MEDIA_NORM = 4
    
    # (1) Engagement Score (50% weight)
    engagement = (
        0.6 * min(post["likes"] / LIKE_NORM, 1.0) + 
        0.4 * min(post["comments"] / COMMENT_NORM, 1.0)
    )

    # (2) Content Quality (30% weight)
    ## Enhanced Sentiment Analysis (TextBlob + Emoji)
    length_bonus = min(len(post["text"])/10, 1.0)
    sentiment = TextBlob(post["text"]).sentiment.polarity  # -1 to 1
    emoji_score = calculate_emoji_sentiment(post["text"])
    combined_sentiment = (sentiment + emoji_score + 1) / 2  # Convert to 0-1 scale
    combined_sentiment = 0.7*combined_sentiment + 0.3*length_bonus

    ## Enhanced Hinglish Movie Relevance
    movie_mentioned_score = check_movie_relevance(post["text"])

    ## Media Boost (Images/Videos)
    media_boost = min(post["media_count"] / MEDIA_NORM, 1.0)

    content = (
        0.7 * combined_sentiment +
        0.1 * movie_mentioned_score +
        0.2 * media_boost
    )

    # (3) Author Reputation (10% weight)
    author = (
        0.4 * min(post["author_content_watched"] / 100, 1.0) +  
        0.3 * min(post["author_reviews_posted"] / 100, 1.0) +
        0.3 * min(post["author_public_watchlists"] / 5, 1.0)
    )

    # (4) Time Decay
    decay_factor = 1 + math.log(1 + post["likes"]/100)
    hours_old = (datetime.now() - post["created_at"]).total_seconds() / 3600
    decay = 0.5 ** (hours_old / (48 * decay_factor))  # Halflife = 2 days

    # Final Weighted Score (0-100)
    raw_score = (0.6 * engagement + 0.3 * content + 0.1 * author) * 100
    final_score = decay * raw_score

    return round(final_score, 1)

# Streamlit UI
st.title("🎬 Movie Post Ranking Demo")
st.markdown("Create and rank movie discussion posts with Mocktale.")

# Sidebar for new post creation
with st.sidebar:
    st.header("Create New Post")
    post_text = st.text_area("Post Content")
    media_count = st.slider("Number of images/videos", 0, 4, 1)
    
    # Author reputation simulation
    st.subheader("Author Reputation")
    col1, col2, col3 = st.columns(3)
    with col1:
        author_watched = st.number_input("Content watched", min_value=0, max_value=5000, value=0, step=1)
    with col2:
        author_reviews = st.number_input("Reviews posted", min_value=0, max_value=5000, value=0, step=1)
    with col3:
        author_watchlists = st.number_input("Public watchlists", min_value=0, max_value=500, value=0, step=1)
    
    if st.button("Submit Post"):
        new_post = {
            "text": post_text,
            "likes": 0,
            "comments": 0,
            "author_content_watched": author_watched,
            "author_reviews_posted": author_reviews,
            "author_public_watchlists": author_watchlists,
            "media_count": media_count,
            "created_at": datetime.now()
        }
        st.session_state.posts.append(new_post)
        st.success("Post created!")

# Main content area
tab1, tab2 = st.tabs(["View Posts", "Ranking Analysis"])

with tab1:
    st.header("Recent Posts")
    
    if not st.session_state.posts:
        st.info("No posts yet. Create one in the sidebar!")
    else:
        for i, post in enumerate(st.session_state.posts):
            with st.expander(f"Post {i+1} (Likes: {post['likes']} | Comments: {post['comments']})"):
                st.write(post["text"])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"👍 Like ({post['likes']})", key=f"like_{i}"):
                        post["likes"] += 1
                        st.rerun()
                with col2:
                    if st.button(f"💬 Comment ({post['comments']})", key=f"comment_{i}"):
                        post["comments"] += 1
                        st.rerun()
                
                # Show score breakdown
                score = calculate_post_score(post)
                st.caption(f"Current score: {score}")
                st.progress(score/100)

with tab2:
    st.header("Ranked Posts")
    
    if st.session_state.posts:
        # Calculate scores and sort
        ranked_posts = sorted(
            [(post, calculate_post_score(post)) for post in st.session_state.posts],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Display as a table
        df = pd.DataFrame([
            {
                "Rank": i+1,
                "Post": post["text"][:50] + ("..." if len(post["text"]) > 50 else ""),
                "Likes": post["likes"],
                "Comments": post["comments"],
                "Media": post["media_count"],
                "Score": score
            }
            for i, (post, score) in enumerate(ranked_posts)
        ])
        
        st.dataframe(df, hide_index=True)
        
        # Show scoring explanation
        with st.expander("How scoring works"):
            st.markdown("""
            **Post Score Formula**:
            - Engagement (60%): Likes (60%) + Comments (40%)
            - Content Quality (30%): 70% consists of this (Sentiment (70%) + Movie Relevance (10%) + Media (20%)) and 30% of posts length
            - Author Reputation (10%): Watched (40%) + Reviews (30%) + Watchlists (30%)
            - Time Decay: Score reduces by half every 48 hours
            """)
    else:
        st.warning("No posts to rank yet!")
