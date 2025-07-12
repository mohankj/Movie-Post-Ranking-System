import streamlit as st
from datetime import datetime, timedelta
from textblob import TextBlob
import emoji
import pandas as pd

# Initialize session state for storing posts
if 'posts' not in st.session_state:
    st.session_state.posts = []

# Scoring functions (your existing code)
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
    
    # Hinglish/Hindi movie terms
    hinglish_terms = [
        "फिल्म", "मूवी", "सिनेमा", "देखा", "देखो", "रिव्यू",
        "एक्टर", "एक्ट्रेस", "डायरेक्टर", "कहानी", "अंत",
        "प्लॉट", "सीन", "मस्त", "बेहतरीन", "घटिया", "बकवास",
        "पैसा वसूल", "टाइमपास", "सुपरहिट", "फ्लॉप"
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
        sum(1 for term in hinglish_terms if term in text_lower) +
        sum(1 for phrase in hinglish_phrases if phrase in text_lower)
    )
    
    # Return score based on number of matches (0.2 base score if no matches)
    return min(1.0, 0.2 + (term_matches * 0.15))

def calculate_post_score(post):
    """
    Calculate a score (0-100) for ranking posts.
    """
    # (1) Engagement Score (50% weight)
    engagement = (
        0.6 * min(post["likes"] / 100, 1.0) + 
        0.4 * min(post["comments"] / 50, 1.0)
    )

    # (2) Content Quality (30% weight)
    ## Enhanced Sentiment Analysis (TextBlob + Emoji)
    sentiment = TextBlob(post["text"]).sentiment.polarity  # -1 to 1
    emoji_score = calculate_emoji_sentiment(post["text"])
    combined_sentiment = (sentiment + emoji_score + 1) / 2  # Convert to 0-1 scale

    ## Enhanced Hinglish Movie Relevance
    movie_mentioned_score = check_movie_relevance(post["text"])

    ## Media Boost (Images/Videos)
    media_boost = min(post["media_count"] / 4, 1.0)

    content = (
        0.5 * combined_sentiment +
        0.3 * movie_mentioned_score +
        0.2 * media_boost
    )

    # (3) Author Reputation (10% weight)
    author = (
        0.4 * min(post["author_content_watched"] / 10000, 1.0) +  
        0.3 * min(post["author_reviews_posted"] / 1000, 1.0) +
        0.3 * min(post["author_public_watchlists"] / 1000, 1.0)
    )

    # (4) Time Decay (10% weight)
    hours_old = (datetime.now() - post["created_at"]).total_seconds() / 3600
    decay = 0.5 ** (hours_old / 48)  # Halflife = 2 days

    # Final Weighted Score (0-100)
    raw_score = (0.5 * engagement + 0.3 * content + 0.1 * author) * 100
    final_score = decay * raw_score

    return round(final_score, 1)

# Streamlit UI
st.title("🎬 Movie Post Ranking Demo")
st.markdown("Create and rank movie discussion posts with Hinglish support")

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
            - Engagement (50%): Likes (60%) + Comments (40%)
            - Content Quality (30%): Sentiment (50%) + Movie Relevance (30%) + Media (20%)
            - Author Reputation (10%): Watched (40%) + Reviews (30%) + Watchlists (30%)
            - Time Decay: Score reduces by half every 48 hours
            """)
    else:
        st.warning("No posts to rank yet!")