import re
import json
import os
import tweepy
import requests
import time
import datetime
import io
from openai import OpenAI
from openai import OpenAIError
from atproto import Client
from difflib import SequenceMatcher
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === API KEYS & AUTHENTICATION ===
# Load environment variables from .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Debugging check (Remove this in production)
print("OpenAI Key:", OPENAI_API_KEY)  # Should print the key if .env is loaded correctly


# Blogger Credentials
BLOGGER_SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOGGER_CREDENTIALS_FILE = os.getenv("BLOGGER_CREDENTIALS_FILE")
BLOGGER_TOKEN_FILE = os.getenv("BLOGGER_TOKEN_FILE")
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID")

# Bluesky Credentials
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")
bsky_client = Client()

# Twitter API Credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
client_twitter = tweepy.Client(
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
)

# === HELPER FUNCTIONS ===
def authenticate_blogger():
    """Authenticate Blogger API and return service."""
    creds = None
    if os.path.exists(BLOGGER_TOKEN_FILE):
        with open(BLOGGER_TOKEN_FILE, 'r') as token:
            creds_data = json.load(token)
            creds = Credentials.from_authorized_user_info(creds_data, BLOGGER_SCOPES)

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(BLOGGER_CREDENTIALS_FILE, BLOGGER_SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(BLOGGER_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())


        except Exception as auth_error:  # ✅ Unique name for clarity
            print(f"❌ Blogger authentication error: {auth_error}")
            return None

    return build('blogger', 'v3', credentials=creds)

# Initialize Blogger Service
blogger_service = authenticate_blogger()

if not blogger_service:
    print("🚨 Blogger authentication failed. Skipping Blogger posting but continuing with social media.")


FIXED_LABEL_POOL = [
    "AI", "Cybersecurity", "IT Leadership", "Data Privacy", "Cloud Security",
    "Machine Learning", "Threat Intelligence", "Zero Trust", "Network Security",
    "Blockchain", "DevSecOps", "Risk Management"
]


# Words and phrases to avoid
avoid_words = [
    "crucial", "vital", "harnessing", "robust", "synergy", "innovative", "optimize",
    "leverage", "holistic", "scalable", "empower", "framework", "pivotal", "comprehensive",
    "facilitate", "ubiquitous", "delve", "compelling", "transformative", "streamline",
    "cutting-edge", "game-changing", "orchestrating operational excellence",
    "dynamic realm of", "unwavering commitment", "navigating complexities", "is key",
    "fostering a culture of", "imperative of harmonizing", "foster",
    "the trenches", "in the thick of it", "hard-earned wisdom",
    "in conclusion", "to sum up", "as a finance professional", "from my years in finance",
    "not just", "more than just", "more than just about", "essential", "firstly", "from the trenches",
    "for good reason", "isn't just about", "also about", "firstly",
    "As an IT professional", "As a CIO", "As a technology leader",
    "From my experience in IT", "As someone in the tech industry",
    "From my years in leadership", "As someone who has worked in IT",
    "From the perspective of a CIO", "As an experienced IT leader"
]

def remove_avoid_words(content, words_to_remove):  # ✅ Clearer parameter name
    """Remove overused AI terms from content efficiently"""
    pattern = re.compile(r'\b' + '|'.join(map(re.escape, words_to_remove)) + r'\b', re.IGNORECASE)
    return pattern.sub('', content).strip()

def validate_url(url):
    """Ensure URLs start with https://"""
    if not url.startswith(("http://", "https://")):
        return "https://" + url.strip()
    return url


# === CONTENT GENERATION ===
# ✅ Append Signature with Formatted Social Media Icons
def format_signature(format_type="html"):
    """Returns a formatted signature based on the platform."""

    if format_type == "html":
        return """
         <p style="font-weight: bold;">In partnership,<br>
         Tim</p>
         <p style="font-weight: bold; font-size: 1.1em; color: #0056b3;">
         <em>Find me here:</em></p>
         <p>
           <a href="https://timgabaree.com" target="_blank">
             <img src="https://timgabaree.com/media/timgabaree_profile7_200x200.png" width="32" height="32" alt="Website">
           </a>
           <a href="https://timgabaree.blogspot.com" target="_blank">
             <img src="https://timgabaree.com/media/social_media_blogger_icon.png" width="32" height="32" alt="Blog">
           </a>
           <a href="https://linkedin.com/in/tim-gabaree" target="_blank">
             <img src="https://timgabaree.com/media/social_media_linkedin_icon.png" width="32" height="32" alt="LinkedIn">
           </a>
          <a href="https://x.com/timgabaree/" target="_blank">
             <img src="https://timgabaree.com/media/logo-black.png" width="32" height="32" alt="X.com">
           </a>
          <a href="https://bsky.app/profile/timgabaree.bsky.social" target="_blank">
             <img src="https://timgabaree.com/media/Bluesky_Logo.png" width="32" height="32" alt="BlueSky">
           </a>
         </p>
         """

    elif format_type == "twitter":
        return """\n\n
        In partnership,\n
        Tim\n\n
        Find me here: \n
        🌐 Website: https://timgabaree.com\n
        📝 Blog: https://timgabaree.blogspot.com\n
        🔗 LinkedIn: https://linkedin.com/in/tim-gabaree
        """

    return ""

TOPIC_HISTORY_FILE = "past_topics.json"

def load_past_topics():
    """Load past blog topics from a JSON file, handling file errors."""
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file) or []  # Ensure it returns a list
        except (json.JSONDecodeError, IOError):
            print("⚠️ Warning: past_topics.json is corrupted. Resetting...")
            return []
    return []  # Always return a list, never None

def save_past_topic(topic: str):
    """Save a new blog topic to the JSON file."""
    past_topics = load_past_topics()

    # Keep only the last 30 topics
    past_topics.insert(0, topic)
    past_topics = past_topics[:30]

    try:
        with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as file:
            buffer = io.StringIO()
            json.dump(past_topics, buffer, ensure_ascii=False, indent=4)
            file.write(buffer.getvalue())
    except IOError as io_error:  # ✅ Renamed to 'io_error' for clarity
        print(f"❌ Error saving past topics: {io_error}")

def get_existing_blog_titles(limit=30):
    """Fetch the last 30 blog post titles from Blogger."""
    try:
        posts = blogger_service.posts().list(blogId=BLOGGER_BLOG_ID, maxResults=limit, orderBy="PUBLISHED").execute()
        return [post["title"] for post in posts.get("items", [])]
    except Exception as fetch_error:  # ✅ Renamed to 'fetch_error'
        print(f"Error fetching blog posts: {fetch_error}")
        return []


def select_fixed_labels(content):
    """Select two fixed labels from a predefined pool based on relevance to the blog content."""
    prompt = f"""
    The following blog post discusses IT-related topics, including AI, cybersecurity, and technology leadership.
    Your task is to select **two** relevant labels from this predefined list that best match the content:
    {', '.join(FIXED_LABEL_POOL)}

    Ensure:
    - The labels **must be from the provided list**.
    - The labels should **accurately describe the core topics** of the blog.
    - Do **not** select labels that are too similar to each other.

    Blog Post Content:
    {content[:1000]}  # ✅ First 1000 characters to give AI context
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.6
        )

        fixed_labels = response.choices[0].message.content.strip().split("\n")
        fixed_labels = [label.strip() for label in fixed_labels if
                        label in FIXED_LABEL_POOL]  # Ensure they exist in the pool

        return fixed_labels[:2] if len(fixed_labels) >= 2 else ["AI", "Cybersecurity"]  # ✅ Fallback if AI fails

    except Exception as error:
        print(f"❌ Fixed Label Selection Error: {error}")
        return ["AI", "Cybersecurity"]


def generate_labels_from_ai(content, fixed_labels):
    """Generate two AI-based labels based on blog content, ensuring they differ from fixed labels."""
    prompt = f"""
    The following blog post discusses IT topics such as AI, cybersecurity, or leadership.
    Your task is to generate **two relevant labels** (tags) for this blog that:
    - Are **different** from the fixed labels: {', '.join(fixed_labels)}
    - Are **concise** (one or two words max).
    - **Avoid generic words** (e.g., "Technology", "Digital").
    - Are **relevant to the blog content**.
    - Do **not** number the labels (e.g., do NOT output "1. AI Security, 2. Compliance").

    Blog Post Content:
    {content[:1000]}  # ✅ First 1000 characters to give AI context
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.6
        )

        ai_labels = response.choices[0].message.content.strip().split("\n")

        # ✅ Clean up AI-generated labels: remove numbering, extra spaces, and ensure uniqueness
        ai_labels = [re.sub(r'^\d+\.\s*', '', label).strip() for label in ai_labels if
                     label and label not in fixed_labels]

        return ai_labels[:2] if len(ai_labels) >= 2 else ["Tech Trends", "IT Strategy"]  # ✅ Fallback

    except Exception as error:
        print(f"❌ AI Label Generation Error: {error}")
        return ["Tech Trends", "IT Strategy"]

def extract_keywords_from_title(title):
    """Extract meaningful keywords from a blog title."""
    words = re.findall(r'\b\w+\b', title.lower())  # Extract words, remove punctuation
    return set(words)  # Return as a unique set

def is_topic_duplicate(new_topic, existing_titles, threshold=0.8):
    """Check if the new topic is too similar to an existing blog post using string similarity."""
    for title in existing_titles:
        similarity = SequenceMatcher(None, new_topic.lower(), title.lower()).ratio()
        if similarity >= threshold:
            print(f"⚠️ Duplicate topic detected: '{new_topic}' is {similarity:.2%} similar to '{title}'")
            return True
    return False

def generate_unique_topic(existing_titles, retries=5):
    """Use AI to generate a unique blog topic and ensure it's not similar to previous topics."""
    last_30_titles = load_past_topics()[:30]  # Load last 30 topics

    for retry_count in range(retries):  # ✅ Clearer variable name
        print(f"🔄 Generating AI-based topic (Attempt {retry_count + 1})...")

        # AI prompt to generate new topics
        topic_prompt = (
            f"Generate a unique and engaging blog post topic about AI, cybersecurity, IT leadership, servant leadership, mentoring, or collaboration. "
            f"Optimize it for professional readers and monetization potential. "
            f"Do NOT generate topics similar to these recent ones: {', '.join(last_30_titles)}. "
            f"The title must be concise, well-formatted, and free of unnecessary words. "
            f"Ensure proper grammar, use only real English words, and avoid jargon or newly coined terms. "
            f"Make it relevant to current industry trends with strong engagement potential."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": topic_prompt}],
                max_tokens=20,
                temperature=0.7,
                timeout=15
            )

            new_topic = response.choices[0].message.content.strip()

            if not is_topic_duplicate(new_topic, existing_titles) and new_topic not in last_30_titles:
                print(f"✅ Selected unique topic: {new_topic!r}")
                return new_topic
        except requests.exceptions.Timeout:
            print("⚠️ OpenAI API timed out while generating a topic. Retrying...")
            time.sleep(2)
        except Exception as error:  # ✅ Clear and unique variable name
            print(f"❌ Error generating topic: {error}")
            return None

    print("❌ Could not generate a unique topic after multiple attempts. Using fallback.")
    return "Cybersecurity and IT Leadership Trends in 2025"


def generate_blog_post():
    """Generate a full blog post with dynamic topic selection and deduplication."""
    existing_titles = get_existing_blog_titles()
    topic = generate_unique_topic(existing_titles)

    if not topic:
        print("⚠️ No unique topic found. Skipping blog post generation.")
        return None

    prompt = f"""
    Write a blog post about {topic}, ensuring it focuses on AI, cybersecurity, or IT leadership. 
    Avoid generic discussions—provide actionable insights, industry trends, or leadership strategies. 
    Do not use any of the words or phrases listed in {avoid_words}. 
    Begin directly with the topic—do not introduce the author or their background. 
    Keep the tone semi-formal and practical, using contractions where appropriate. 
    Ensure the title appears on the first line in an <h1> tag. 
    Format the entire blog post using proper HTML tags, with each paragraph wrapped in <p> tags.
    """

    print(f"✅ Generating blog post on: {topic!r}")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.4,
            timeout=30
        )

        post_content = response.choices[0].message.content.strip()

        # Append Signature
        full_post = post_content + format_signature("html")

        # Save the new topic after a successful blog post generation
        save_past_topic(topic)

        return full_post

    # Inside generate_blog_post()
    except Exception as error:  # ✅ Uses a unique, meaningful variable name
        if isinstance(error, OpenAIError):
            print(f"⚠️ OpenAI API Error: {error}. Using fallback content.")
            return "<h1>IT Strategy & Cybersecurity Insights</h1><p>We're experiencing technical issues. Stay tuned for updates!</p>"
        else:
            print(f"❌ Unexpected error: {error}")
            return None

def extract_topic_from_blog(content):
    """Extracts the blog title from the content by searching for the first <h1> tag."""
    match = re.search(r'<h1>(.*?)</h1>', content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "General IT Leadership"  # Default fallback if no title is found


def post_to_blogger(content):
    """Post blog content to Blogger with dynamically selected fixed labels and AI-generated labels."""
    try:
        print("📢 Posting to Blogger...")

        fixed_labels = select_fixed_labels(content)  # ✅ Dynamically selected fixed labels
        ai_labels = generate_labels_from_ai(content, fixed_labels)  # ✅ AI-generated labels

        all_labels = fixed_labels + ai_labels  # ✅ Combine fixed + AI labels

        # Extract blog title
        topic = extract_topic_from_blog(content)

        # Ensure content does not duplicate the title
        content_without_title = re.sub(rf"<h1>{re.escape(topic)}</h1>\s*", "", content, count=1)

        post_body = {
            'content': content_without_title,
            'labels': all_labels,  # ✅ Use final labels list
            'title': topic
        }

        response = blogger_service.posts().insert(
            blogId=BLOGGER_BLOG_ID,
            body=post_body,
            isDraft=False
        ).execute()

        blogger_url = response.get('url', '').strip()

        if blogger_url:
            print(f"✅ Successfully posted on Blogger: {blogger_url} with labels {all_labels}")
            return blogger_url, all_labels  # ✅ Return blog URL and labels
        else:
            raise ValueError("⚠️ Blogger post URL is missing.")

    except Exception as error:
        print(f"❌ Blogger API Error: {error}")
        return None, None

# Define common filler words to exclude from hashtags
FILLER_WORDS = {"the", "of", "and", "to", "in", "on", "for", "a", "with", "is", "at", "by", "as"}


### **GENERATE DYNAMIC HASHTAGS FROM BLOG TOPIC** ###
def generate_hashtags(labels, limit=4):
    """Generate hashtags from the assigned Blogger labels, ensuring correct formatting."""
    hashtags = [f"#{label.replace(' ', '')}" for label in labels if len(label) > 1]  # Ensure no 1-letter hashtags
    return " ".join(hashtags[:limit])  # ✅ Limit hashtags to avoid clutter

### **GENERATE SOCIAL MEDIA PROMO WITH DYNAMIC HASHTAGS** ###
def generate_social_media_promo(blog_url, topic):
    """Generate a short social media promo with a link to the blog post and relevant hashtags."""
    prompt = f"""
    Write a short and engaging summary of a blog post titled '{topic}' located at {blog_url}.
    It should be under 280 characters and include 2-3 relevant hashtags.
    """
    print("Generating social media promo...")
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        promo_text = response.choices[0].message.content.strip()
        return promo_text[:277] + "..." if len(promo_text) > 280 else promo_text
    except requests.exceptions.Timeout:
        print("Error: OpenAI API timed out while generating social media promo.")
    except Exception as error:
        print(f"Error: {error}")
    return None


### **POST TO BLUESKY WITH DYNAMIC HASHTAGS** ###
def mark_urls(text):
    """Extract URLs from text and return their start/end positions for facets."""
    url_regex = r"(https?://[^\s]+)"
    matches = re.finditer(url_regex, text)

    return [{"start": match.start(), "end": match.end(), "url": match.group(0)} for match in matches]


def post_to_bluesky(blogger_url, topic, labels):
    """Posts to Bluesky with a clickable link and dynamic hashtags."""

    print("📢 Logging into Bluesky before posting...")
    try:
        bsky_client.login(BSKY_HANDLE, BSKY_PASSWORD)
        print("✅ Successfully logged into Bluesky")
    except Exception as e:
        print(f"❌ Bluesky login failed: {e}")
        return

    blogger_url = validate_url(blogger_url)  # ✅ Ensures HTTPS format

    hashtags = generate_hashtags(labels, limit=4)  # ✅ Use same labels for hashtags
    post_text = f"Check out my latest blog post: {topic}!\n\n{blogger_url}\n\n{hashtags}"

    if len(post_text) > 300:
        post_text = post_text[:297] + "..."

    url_data = mark_urls(post_text)

    facets = [
        {
            "index": {"byteStart": url["start"], "byteEnd": url["end"]},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url["url"]}]
        }
        for url in url_data
    ] if url_data else None

    post_payload = {
        "repo": BSKY_HANDLE,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": post_text,
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "facets": facets
        }
    }

    try:
        response = bsky_client.com.atproto.repo.create_record(data=post_payload)

        if hasattr(response, "uri") and response.uri:
            print(f"✅ Successfully posted on Bluesky. Post URI: {response.uri}")
        elif hasattr(response, "cid") and response.cid:
            print(f"✅ Post was accepted, but URI is missing. CID: {response.cid}")
        else:
            print(f"⚠️ Post request was sent but response format is unexpected: {response}")
    except Exception as error:
        print(f"❌ Bluesky API Error: {error}")

### **POST TO TWITTER (X) WITH DYNAMIC HASHTAGS** ###
def post_to_twitter(blogger_url, topic, labels):
    """Post a short promo tweet linking to the blog post with dynamic hashtags."""
    print("📢 Posting blog promo to Twitter...")

    blogger_url = validate_url(blogger_url)  # ✅ Ensures HTTPS format
    promo_text = generate_social_media_promo(blogger_url, topic)  # ✅ Generate text
    hashtags = generate_hashtags(labels, limit=3)  # ✅ Use the same labels for hashtags

    if promo_text:
        base_tweet = f"{promo_text} {blogger_url} {hashtags}"  # ✅ Single tweet with promo, link, and hashtags

        # ✅ Ensure tweet does not exceed 280 characters
        max_tweet_length = 280
        if len(base_tweet) > max_tweet_length:
            remaining_space = max_tweet_length - len(blogger_url) - len(hashtags) - 5  # Space for "..."
            trimmed_promo = promo_text[:remaining_space] + "..."
            tweet_text = f"{trimmed_promo} {blogger_url} {hashtags}"  # ✅ All in one tweet
        else:
            tweet_text = base_tweet  # ✅ Fits within 280 chars

        try:
            response = client_twitter.create_tweet(text=tweet_text)
            if response.data:
                print(f"✅ Successfully posted blog promo on Twitter. Tweet ID: {response.data['id']}")
            else:
                print("⚠️ Tweet posted, but response data is empty.")
        except tweepy.TweepyException as error:
            print(f"❌ Error posting blog promo tweet: {error}")
    else:
        print("⚠️ Skipping Twitter promo due to content generation failure.")

### **POST FULL BLOG TO TWITTER PREMIUM (X)** ###
def strip_html_tags(text):
    """Remove HTML tags and clean up spacing for Twitter formatting."""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    return text.replace("\n\n", "\n")  # Ensure single line breaks


def format_twitter_post(full_post, blogger_url):
    """Prepare content for Twitter by removing HTML and ensuring proper formatting."""
    plain_text = strip_html_tags(full_post)

    # ✅ Ensure the correct blog post URL is included
    formatted_text = f"🚀 {plain_text[:250]}...\n\nRead more: {blogger_url}"

    return formatted_text


def post_to_twitter_premium(full_post, blogger_url, labels):
    """Post a teaser (25% of the content) to Twitter Premium (X) with hashtags and a link."""
    print("📢 Logging into X/Twitter before posting...")

    try:
        global client_twitter  # Ensure we're using the global variable
        client_twitter = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        print("✅ Successfully logged into Twitter Premium")
    except Exception as e:
        print(f"❌ Twitter login failed: {e}")
        return

    # Ensure URLs start with https://
    blogger_url = validate_url(blogger_url)

    # Generate hashtags from labels
    hashtags = generate_hashtags(labels, limit=4)
    print(f"🔹 Hashtags generated: {hashtags}")  # ✅ Debugging print

    # Strip HTML tags for clean formatting
    plain_text = strip_html_tags(full_post)

    # Determine the teaser length (25% of the total post, max 5,000 characters)
    teaser_length = min(len(plain_text) // 4, 5000)
    teaser_text = plain_text[:teaser_length].strip()

    # Ensure teaser ends cleanly (avoid cutting off mid-word)
    if len(teaser_text) < len(plain_text):
        teaser_text += "..."  # ✅ Indicate more content is available

    # Append blog URL and hashtags
    tweet_text = f"{teaser_text}\n\nRead more: {blogger_url}\n\n{hashtags}"

    print(f"📢 Final Twitter Premium Teaser:\n{tweet_text[:500]}...")  # ✅ Debugging print (first 500 chars)

    try:
        response = client_twitter.create_tweet(text=tweet_text)

        if response and response.data:
            print(f"✅ Successfully posted teaser on Twitter Premium. Tweet ID: {response.data.get('id')}")
        else:
            print("⚠️ Tweet posted, but response data is empty.")
    except tweepy.TweepyException as error:
        print(f"❌ Twitter API Error: {error}")

# ✅ **Now add this at the very end of the script**
if __name__ == "__main__":
    print("🔄 Starting full blog automation process...")

    # ✅ Step 1: Authenticate to Blogger
    blogger_service = authenticate_blogger()

    if not blogger_service:
        print("🚨 Blogger authentication failed. Skipping Blogger posting but continuing with social media.")

    # ✅ Step 2: Generate a Blog Post
    blog_post_content = generate_blog_post()
    if not blog_post_content:
        print("⚠️ Blog post generation failed. Exiting process.")
    else:
        print("✅ Blog post generated successfully.")

        # ✅ Step 3: Post to Blogger
        blogger_url, labels = None, None
        if blogger_service:
            blogger_url, labels = post_to_blogger(blog_post_content)  # ✅ Get URL and labels

        if blogger_url:
            print(f"✅ Blog post published: {blogger_url}")

            # ✅ Step 4: Post to Social Media with matching hashtags
            topic = extract_topic_from_blog(blog_post_content)
            hashtags = generate_hashtags(labels, limit=3)  # ✅ Use same labels for hashtags

            post_to_bluesky(blogger_url, topic, labels)
            post_to_twitter_premium(blog_post_content, blogger_url, labels)  # ✅ Only Twitter Premium post

        else:
            print("⚠️ Blog posting failed. Skipping social media promotion.")