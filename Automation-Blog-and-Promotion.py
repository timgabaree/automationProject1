#!/usr/bin/env python3
"""
Automation Blog and Promotion Script

This script generates a blog post using OpenAI's GPT-4 and DALL·E, uploads the post
to Blogger, and then promotes it on Bluesky and Twitter. Images are generated via DALL·E,
and the image for Bluesky is compressed/resized to meet the file size limits. The image for Blogger is
uploaded to Google Drive so that Blogger can retrieve it via a public URL.

Note: This script uses several APIs (OpenAI, Google Drive, Blogger, Bluesky, Twitter).
Make sure the credentials in your .env file are correctly set.
"""

import re
import json
import os
import tweepy
import requests
import time
import datetime
import io
import mimetypes
import openai
from atproto import Client
from difflib import SequenceMatcher
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2 import service_account
from PIL import Image  # For image processing

# ----------------------------- Logging Setup -----------------------------
LOG_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Logs/automationProject1"
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "script_log.txt")
os.makedirs(LOG_DIRECTORY, exist_ok=True)  # Ensure log directory exists

def log_message(message):
    """Append a timestamped log message to script_log.txt."""
    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{datetime.datetime.now()} - {message}\n")

log_message("Script started")

# ----------------------------- Load Environment & API Keys -----------------------------
CREDENTIALS_PATH = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/Credentials/automationProject1"
env_path = os.path.join(CREDENTIALS_PATH, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print("⚠️ WARNING: .env file not found!")
load_dotenv()  # Load environment variables

# OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Google Drive Credentials
DRIVE_CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SCOPES = ['https://www.googleapis.com/auth/drive']
GOOGLE_DRIVE_FOLDER_ID = "14fjoDVxGY5OZwuGMmzqbNE5nCqQUu1jH"

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

# ----------------------------- Paths -----------------------------
MEDIA_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/automationProject1/media"
FALLBACK_IMAGE_DIRECTORY = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/automationProject1/media/fallback_images"
os.makedirs(MEDIA_DIRECTORY, exist_ok=True)
TOPIC_HISTORY_FILE = "past_topics.json"

# ----------------------------- Helper Functions -----------------------------

def authenticate_blogger():
    """
    Authenticate to Blogger using OAuth credentials from the .env file.
    Returns a Blogger service object.
    """
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
            with open(BLOGGER_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        except Exception as auth_error:
            print(f"❌ Blogger authentication error: {auth_error}")
            return None
    return build('blogger', 'v3', credentials=creds)

# Initialize Blogger service
blogger_service = authenticate_blogger()
if not blogger_service:
    print("🚨 Blogger authentication failed. Skipping Blogger posting but continuing with social media.")

# Fixed labels and words to avoid (for topic and label generation)
FIXED_LABEL_POOL = [
    "AI", "Cybersecurity", "IT Leadership", "Data Privacy", "Cloud Security",
    "Machine Learning", "Threat Intelligence", "Zero Trust", "Network Security",
    "Blockchain", "DevSecOps", "Risk Management"
]
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

def remove_avoid_words(content, words_to_remove):
    """Remove overused words or phrases from content."""
    pattern = re.compile(r'\b' + '|'.join(map(re.escape, words_to_remove)) + r'\b', re.IGNORECASE)
    return pattern.sub('', content).strip()

def validate_url(url):
    """Ensure the URL starts with https://; if not, prepend it."""
    if not url.startswith(("http://", "https://")):
        return "https://" + url.strip()
    return url

def format_signature(format_type="html"):
    """
    Return a signature block in HTML or plain text format.
    Used to append a signature to blog posts.
    """
    if format_type == "html":
        return """
         <p style="font-weight: bold;">In partnership,<br>Tim</p>
         <p style="font-weight: bold; font-size: 1.1em; color: #0056b3;"><em>Find me here:</em></p>
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
        return "\n\nIn partnership,\nTim\n\nFind me here:\n🌐 Website: https://timgabaree.com\n📝 Blog: https://timgabaree.blogspot.com\n🔗 LinkedIn: https://linkedin.com/in/tim-gabaree"
    return ""

def load_past_topics():
    """Load past blog topics from a JSON file for deduplication."""
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file) or []
        except (json.JSONDecodeError, IOError):
            print("⚠️ Warning: past_topics.json is corrupted. Resetting...")
            return []
    return []

def save_past_topic(topic: str):
    """Save a new blog topic to the JSON file."""
    past_topics = load_past_topics()
    past_topics.insert(0, topic)
    past_topics = past_topics[:30]
    try:
        with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as file:
            buffer = io.StringIO()
            json.dump(past_topics, buffer, ensure_ascii=False, indent=4)
            file.write(buffer.getvalue())
    except IOError as io_error:
        print(f"❌ Error saving past topics: {io_error}")

def get_existing_blog_titles(limit=30):
    """Retrieve the titles of recent blog posts from Blogger."""
    try:
        posts = blogger_service.posts().list(blogId=BLOGGER_BLOG_ID, maxResults=limit, orderBy="PUBLISHED").execute()
        return [post["title"] for post in posts.get("items", [])]
    except Exception as fetch_error:
        print(f"Error fetching blog posts: {fetch_error}")
        return []

def select_fixed_labels(content):
    """
    Use AI to select two fixed labels from a predefined pool that match the blog content.
    This helps in categorizing the blog post.
    """
    prompt = f"""
    The following blog post discusses IT-related topics, including AI, cybersecurity, and technology leadership.
    Select two labels from the following list that best describe the content:
    {', '.join(FIXED_LABEL_POOL)}
    Blog Post Content (first 1000 characters):
    {content[:1000]}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.6
        )
        fixed_labels = response.choices[0].message.content.strip().split("\n")
        fixed_labels = [label.strip() for label in fixed_labels if label in FIXED_LABEL_POOL]
        return fixed_labels[:2] if len(fixed_labels) >= 2 else ["AI", "Cybersecurity"]
    except Exception as error:
        print(f"❌ Fixed Label Selection Error: {error}")
        return ["AI", "Cybersecurity"]

def generate_labels_from_ai(content, fixed_labels):
    """
    Use AI to generate two additional labels based on the blog content,
    ensuring they differ from the fixed labels.
    """
    prompt = f"""
    The following blog post discusses IT topics such as AI, cybersecurity, or leadership.
    Generate two concise, relevant labels (one or two words each) that differ from these fixed labels: {', '.join(fixed_labels)}.
    Blog Post Content (first 1000 characters):
    {content[:1000]}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.6
        )
        ai_labels = response.choices[0].message.content.strip().split("\n")
        ai_labels = [re.sub(r'^\d+\.\s*', '', label).strip() for label in ai_labels if label and label not in fixed_labels]
        return ai_labels[:2] if len(ai_labels) >= 2 else ["Tech Trends", "IT Strategy"]
    except Exception as error:
        print(f"❌ AI Label Generation Error: {error}")
        return ["Tech Trends", "IT Strategy"]

def extract_keywords_from_title(title):
    """Extract unique keywords from the blog title."""
    words = re.findall(r'\b\w+\b', title.lower())
    return set(words)

def is_topic_duplicate(new_topic, existing_titles, threshold=0.8):
    """Check if the new topic is too similar to any existing topic."""
    for title in existing_titles:
        similarity = SequenceMatcher(None, new_topic.lower(), title.lower()).ratio()
        if similarity >= threshold:
            print(f"⚠️ Duplicate topic detected: '{new_topic}' is {similarity:.2%} similar to '{title}'")
            return True
    return False

def generate_unique_topic(existing_titles, retries=5):
    """
    Use AI to generate a unique blog topic.
    It ensures the new topic is not too similar to any of the existing topics.
    """
    last_30_titles = load_past_topics()[:30]
    for retry_count in range(retries):
        print(f"🔄 Generating AI-based topic (Attempt {retry_count + 1})...")
        topic_prompt = (
            f"Generate a unique and engaging blog post topic about AI, cybersecurity, IT leadership, servant leadership, mentoring, or collaboration. "
            f"Ensure it is concise and free of unnecessary words. Do NOT generate a topic similar to these: {', '.join(last_30_titles)}."
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
        except Exception as error:
            print(f"❌ Error generating topic: {error}")
            return None
    print("❌ Could not generate a unique topic after multiple attempts. Using fallback.")
    return "Cybersecurity and IT Leadership Trends in 2025"

def generate_blog_post():
    """
    Generate a blog post using AI.
    Returns a tuple of (post content, topic) without embedding the title in the body.
    """
    existing_titles = get_existing_blog_titles()
    topic = generate_unique_topic(existing_titles)
    if not topic:
        print("⚠️ No unique topic found. Skipping blog post generation.")
        return None, None

    prompt = f"""
    Write a blog post about {topic} that focuses on AI, cybersecurity, or IT leadership. 
    Provide actionable insights, industry trends, or leadership strategies without including the title in the body.
    Format the post using HTML, wrapping each paragraph in <p> tags. Do not include an <h1> tag.
    Avoid using phrases that might indicate the post was generated by AI.
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
        full_post = post_content + format_signature("html")
        save_past_topic(topic)
        return full_post, topic
    except Exception as error:
        print(f"❌ Error generating blog post: {error}")
        return None, None

def generate_blog_image(topic):
    """
    Generate an AI image at 1024x1024 based on the topic,
    save it as a PNG, and return the file path.
    If the generation fails, return a fallback image.
    """
    try:
        print(f"🎨 Generating AI image for topic: {topic}")
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"A futuristic, high-tech concept art related to {topic}. Vibrant colors, engaging and dynamic.",
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url if response and response.data else None
        if not image_url:
            raise ValueError("OpenAI API returned no image URL.")
        image_path = os.path.join(MEDIA_DIRECTORY, f"{topic.replace(' ', '_')}.png")
        img_data = requests.get(image_url).content
        with open(image_path, "wb") as img_file:
            img_file.write(img_data)
        if os.path.exists(image_path):
            print(f"✅ AI Image saved: {image_path}")
            return image_path
        else:
            print(f"🔍 [DEBUG] Full AI Image Response: {response}")
            raise FileNotFoundError(f"Image not saved: {image_path}")
    except (openai.OpenAIError, requests.RequestException, ValueError, FileNotFoundError) as e:
        print(f"❌ AI Image generation failed: {e}")
    fallback_image = get_fallback_image(topic)
    print(f"⚠️ Using fallback image instead: {fallback_image}")
    return fallback_image

def generate_image_filename(category):
    """Generate a timestamped filename for an image based on the category."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_{category}.png"
    return os.path.join(MEDIA_DIRECTORY, filename)

def get_fallback_image(category):
    """
    Return a fallback image path based on the category if AI image generation fails.
    """
    fallback_map = {
        "ai": "ai_fallback_image.png",
        "cybersecurity": "cybersecurity_fallback_image.png",
        "it_leadership": "it_leadership_fallback_image.png"
    }
    # Ensure the fallback directory is defined
    fallback_dir = "/Users/timgabaree/Library/CloudStorage/Dropbox/Projects/Python/automationProject1/media/fallback_images"
    fallback_filename = fallback_map.get(category.lower(), "ai_fallback_image.png")
    fallback_path = os.path.join(fallback_dir, fallback_filename)
    print(f"⚠️ Using fallback image: {fallback_path}")
    return fallback_path

def authenticate_google_drive():
    """
    Authenticate with the Google Drive API using a service account.
    Returns a Drive service object.
    """
    creds = service_account.Credentials.from_service_account_file(
        DRIVE_CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def upload_blog_image_to_drive(image_path):
    """
    Upload an image to Google Drive so that Blogger can retrieve it.
    Returns a public URL for the image.
    """
    try:
        print(f"📤 Uploading image to Google Drive: {image_path}")
        drive_service = authenticate_google_drive()
        file_metadata = {
            "name": os.path.basename(image_path),
            "mimeType": mimetypes.guess_type(image_path)[0],
            "parents": [GOOGLE_DRIVE_FOLDER_ID],
        }
        media = MediaFileUpload(image_path, mimetype=file_metadata["mimeType"])
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        drive_service.permissions().create(
            fileId=uploaded_file["id"],
            body={"role": "reader", "type": "anyone"},
        ).execute()
        public_url = f"https://drive.google.com/thumbnail?id={uploaded_file['id']}&sz=w1000"
        print(f"✅ Image uploaded to Google Drive: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ Google Drive upload failed: {e}")
        return None

def extract_blog_quote(content):
    """
    Extract a key quote from the blog post by splitting at punctuation.
    Returns the first sentence as a highlight.
    """
    try:
        sentences = re.split(r'(?<=[.!?])\s+', content)
        return sentences[0] if sentences else "A powerful insight on leadership, AI, and cybersecurity."
    except Exception as e:
        print(f"❌ Quote extraction failed: {e}")
        return "A powerful insight on leadership, AI, and cybersecurity."

def clean_blog_content(content):
    """
    Remove any <h1> tags from the blog content.
    The title is handled separately, so it should not appear in the body.
    """
    return re.sub(r'<h1>.*?</h1>', '', content, flags=re.IGNORECASE).strip()

def post_to_blogger(content, topic):
    """
    Post the blog content to Blogger.
    Generates an AI image, uploads it to Google Drive, and inserts it into the post content.
    The title is sanitized and set in the Blogger title field.
    """
    print("📢 Posting to Blogger...")
    try:
        # Generate the AI image for the blog post
        final_image_path = generate_blog_image(topic)
        if not final_image_path or not os.path.exists(final_image_path):
            print("❌ [ERROR] Missing image! Using fallback.")
            final_image_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")

        # Upload the image to Google Drive and get its public URL
        blog_image_url = upload_blog_image_to_drive(final_image_path)

        # Insert the image into the blog content if upload succeeded
        if blog_image_url:
            alt_text = topic.replace('"', '').replace("'", "&#39;")
            image_html = f'''
                <div style="text-align:center;">
                    <img src="{blog_image_url}" alt="{alt_text}" 
                         style="max-width:750px; width:100%; height:auto; margin-bottom:20px; border-radius:8px;">
                </div>
            '''
            content_with_image = f"{image_html}\n\n{content}"
        else:
            content_with_image = content

        # Generate labels for the post
        fixed_labels = select_fixed_labels(content_with_image)
        ai_labels = generate_labels_from_ai(content_with_image, fixed_labels)
        all_labels = fixed_labels + ai_labels

        # Sanitize the title to remove extraneous quotes
        sanitized_topic = topic.replace('"', '').replace("'", "&#39;")

        # Prepare the post body for Blogger
        post_body = {
            'content': content_with_image,
            'labels': all_labels,
            'title': sanitized_topic
        }

        # Post to Blogger
        response = blogger_service.posts().insert(
            blogId=BLOGGER_BLOG_ID,
            body=post_body,
            isDraft=False
        ).execute()
        blogger_url = response.get('url', '').strip()
        if blogger_url:
            print(f"✅ Successfully posted on Blogger: {blogger_url}")
            return blogger_url, blog_image_url, all_labels
        else:
            raise ValueError("⚠️ Blogger post URL is missing.")
    except Exception as error:
        print(f"❌ Blogger API Error: {error}")
        return None, None, []

def generate_hashtags(labels, limit=4):
    """
    Generate dynamic hashtags from the provided labels.
    Hashtags are formed by removing spaces and prefixing with '#'.
    """
    hashtags = [f"#{label.replace(' ', '')}" for label in labels if len(label) > 1]
    return " ".join(hashtags[:limit])

def generate_social_media_promo(blog_url, topic):
    """
    Generate a short, engaging social media promo for the blog post.
    This promo includes the blog URL and 2-3 relevant hashtags.
    """
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

def compress_and_resize_image(image_path, max_size_kb=976, max_dimensions=(720, 720)):
    """
    Resize and compress an image to meet Bluesky's file size limit.
    The image is resized to fit within max_dimensions and compressed until it's under max_size_kb.
    The output is saved as a JPEG.
    """
    if not os.path.exists(image_path):
        print(f"❌ [ERROR] Image does not exist before compression: {image_path}")
        # Return fallback image immediately if not found
        return os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")
    print(f"📢 [DEBUG] Compressing image: {image_path} (Exists: {os.path.exists(image_path)})")
    img = Image.open(image_path)
    # Define the filename for the compressed image
    compressed_image_path = image_path.rsplit(".", 1)[0] + "_compressed.jpg"
    # Resize the image to fit within the specified dimensions while maintaining aspect ratio
    img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)
    quality = 85
    while True:
        img.convert("RGB").save(compressed_image_path, format="JPEG", quality=quality)
        file_size_kb = os.path.getsize(compressed_image_path) / 1024
        print(f"📢 [DEBUG] Compressed image size: {file_size_kb:.2f} KB (Quality: {quality})")
        if file_size_kb <= max_size_kb or quality <= 20:
            break
        quality -= 5
    if os.path.exists(compressed_image_path):
        return compressed_image_path
    else:
        print(f"❌ [ERROR] Compressed image was not saved! Using fallback.")
        return os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image_compressed.jpg")

def mark_urls(text):
    """
    Extract URLs from the text and return a list of dictionaries indicating their positions.
    This is used for creating clickable links in social media posts.
    """
    url_regex = r"(https?://[^\s]+)"
    matches = re.finditer(url_regex, text)
    return [{"start": match.start(), "end": match.end(), "url": match.group(0)} for match in matches]

def post_to_bluesky(blogger_url, topic, all_labels, bluesky_image_path):
    """
    Post a promotional message to Bluesky with a clickable image.
    The image is compressed to meet Bluesky's size restrictions.
    """
    print(f"📢 [DEBUG] Posting blog promo to Bluesky...")
    # Compress and resize image for Bluesky
    bluesky_image_path = compress_and_resize_image(final_image_path, max_size_kb=976, max_dimensions=(720, 720))
    if not bluesky_image_path or not os.path.exists(bluesky_image_path):
        print(f"❌ [ERROR] Compressed image for Bluesky is missing! Using fallback.")
        bluesky_image_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")
    try:
        # Login to Bluesky
        bsky_client.login(BSKY_HANDLE, BSKY_PASSWORD)
        print("✅ Successfully logged into Bluesky")
        blogger_url = validate_url(blogger_url)
        hashtags = generate_hashtags(all_labels, limit=4)
        sanitized_topic = topic.replace('"', '').replace("'", "&#39;")
        post_text = f"Check out my latest blog post: {sanitized_topic}!\n\n{blogger_url}\n\n{hashtags}"
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
        with open(bluesky_image_path, "rb") as img_file:
            image_data = img_file.read()
        uploaded_image = bsky_client.com.atproto.repo.upload_blob(image_data)
        if not uploaded_image or not hasattr(uploaded_image, 'blob'):
            print(f"❌ Failed to upload image to Bluesky: {uploaded_image}")
            return
        print(f"✅ [DEBUG] Successfully uploaded image to Bluesky")
        image_blob = {
            "$type": "blob",
            "ref": {"$link": uploaded_image.blob.ref.link},
            "mimeType": "image/jpeg",
            "size": os.path.getsize(bluesky_image_path)
        }
        external_embed = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": blogger_url,
                "title": sanitized_topic,
                "description": "New blog post on AI, cybersecurity, and IT leadership!",
                "thumb": image_blob
            }
        }
        post_payload = {
            "repo": bsky_client.me.did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": post_text,
                "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "facets": facets,
                "embed": external_embed
            }
        }
        print("🔍 Debugging Bluesky Payload:", json.dumps(post_payload, indent=4))
        response = bsky_client.com.atproto.repo.create_record(data=post_payload)
        print("🔍 Bluesky Response:", response)
        if response and hasattr(response, 'uri'):
            print(f"✅ Successfully posted on Bluesky. Post URI: {response.uri}")
        else:
            print(f"⚠️ Bluesky response format is unexpected: {response}")
    except Exception as e:
        print(f"❌ Bluesky API Error: {e}")

def post_to_twitter(blogger_url, topic, labels, final_image_path):
    """
    Post a promotional tweet on Twitter with the blog URL and hashtags.
    The tweet includes the final image.
    """
    print("📢 Posting blog promo to Twitter...")
    hashtags = generate_hashtags(labels, limit=3)
    sanitized_topic = topic.replace('"', '').replace("'", "&#39;")
    tweet_text = f"🚀 New Blog Post: {sanitized_topic}\n\n{blogger_url}\n\n{hashtags}"
    try:
        if not os.path.exists(final_image_path):
            print(f"⚠️ Warning: Twitter image file not found! Using fallback.")
            final_image_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(final_image_path)
        media_id = [media.media_id]
        response = api_v1.update_status(status=tweet_text, media_ids=media_id)
        if response:
            print(f"✅ Successfully posted blog promo on Twitter. Tweet ID: {response.id}")
        else:
            print("⚠️ Tweet posted, but response data is empty.")
    except tweepy.TweepyException as error:
        print(f"❌ Twitter API Error: {error}")

def strip_html_tags(text):
    """Remove HTML tags from text for plain formatting."""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    return text.replace("\n\n", "\n")

def format_twitter_post(full_post, blogger_url):
    """
    Prepare a tweet text by stripping HTML and appending a link.
    This is used for long-form teaser posts.
    """
    plain_text = strip_html_tags(full_post)
    formatted_text = f"🚀 {plain_text[:250]}...\n\nRead more: {blogger_url}"
    return formatted_text

def post_to_twitter_premium(full_post, blogger_url, labels):
    """
    Post a long-form teaser tweet to Twitter Premium (X) with hashtags.
    """
    print("📢 Logging into X/Twitter before posting...")
    try:
        global client_twitter
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
    blogger_url = validate_url(blogger_url)
    hashtags = generate_hashtags(labels, limit=4)
    print(f"🔹 Hashtags generated: {hashtags}")
    plain_text = strip_html_tags(full_post)
    teaser_length = min(len(plain_text) // 4, 5000)
    teaser_text = plain_text[:teaser_length].strip()
    if len(teaser_text) < len(plain_text):
        teaser_text += "..."
    tweet_text = f"{teaser_text}\n\nRead more: {blogger_url}\n\n{hashtags}"
    print(f"📢 Final Twitter Premium Teaser:\n{tweet_text[:500]}...")
    try:
        response = client_twitter.create_tweet(text=tweet_text)
        if response and response.data:
            print(f"✅ Successfully posted teaser on Twitter Premium. Tweet ID: {response.data.get('id')}")
        else:
            print("⚠️ Tweet posted, but response data is empty.")
    except tweepy.TweepyException as error:
        print(f"❌ Twitter API Error: {error}")

# ----------------------------- Main Execution Block -----------------------------
if __name__ == "__main__":
    print("🔄 Starting full blog automation process...")

    # Step 1: Authenticate to Blogger
    blogger_service = authenticate_blogger()

    # Step 2: Generate a Blog Post (content and topic)
    blog_post_content, topic = generate_blog_post()
    if not blog_post_content or not topic:
        print("⚠️ Blog post generation failed. Exiting process.")
        exit()

    # Step 3: Post the blog to Blogger
    blogger_url, blog_image_url, all_labels = post_to_blogger(blog_post_content, topic)

    # Step 4: Generate the AI Image for the post
    final_image_path = generate_blog_image(topic)
    if not final_image_path or not os.path.exists(final_image_path):
        print("❌ [ERROR] Missing image! Using fallback.")
        final_image_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")
    print(f"📢 [DEBUG] Final image for posting: {final_image_path} (Exists: {os.path.exists(final_image_path)})")

    # Step 5: Compress and resize the image for Bluesky (ensure it's under the size limit)
    bluesky_image_path = compress_and_resize_image(final_image_path, max_size_kb=976, max_dimensions=(720, 720))
    if not bluesky_image_path or not os.path.exists(bluesky_image_path):
        print("❌ [ERROR] Compressed image for Bluesky is missing! Using fallback.")
        bluesky_image_path = os.path.join(FALLBACK_IMAGE_DIRECTORY, "default_fallback_image.png")

    # Step 6: Post to Bluesky with the compressed image
    post_to_bluesky(blogger_url, topic, all_labels, bluesky_image_path)

    # Step 7: Post a promotional tweet to Twitter with the full AI image
    post_to_twitter(blogger_url, topic, all_labels, final_image_path)

    # Step 8: Post a long-form teaser to Twitter Premium
    post_to_twitter_premium(blog_post_content, blogger_url, all_labels)