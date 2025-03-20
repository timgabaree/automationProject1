# Automation Blog and Promotion Script

This project automates the process of generating blog posts using OpenAI's GPT-4 and DALL·E, posting them on Blogger, and promoting them on Bluesky and Twitter. It generates unique blog content and topics, creates an AI-generated image (with fallback support), uploads the image to Google Drive for Blogger retrieval, and posts promotional messages on multiple social platforms.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Creating a Virtual Environment](#creating-a-virtual-environment)
  - [Installing Dependencies](#installing-dependencies)
  - [Sample requirements.txt](#sample-requirementstxt)
- [Configuration](#configuration)
  - [.env File Setup](#env-file-setup)
  - [Directory Setup](#directory-setup)
- [Usage](#usage)
- [Cron Job Setup](#cron-job-setup)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contact](#contact)

---

## Overview

This script handles the full workflow:
1. **Blog Post Generation:** Uses GPT-4 to generate a unique blog post and topic.
2. **Image Generation:** Uses DALL·E to generate an AI image based on the topic.
3. **Image Processing:** Compresses and resizes the image for Bluesky (ensuring it’s under 976 KB and within 720×720 pixels).
4. **Image Hosting:** Uploads the image to Google Drive so that Blogger can retrieve it via a public URL.
5. **Blog Posting:** Posts the blog to Blogger with the generated content and labels.
6. **Social Media Promotion:** Posts promotional messages on Bluesky, Twitter, and Twitter Premium with dynamic hashtags and a teaser.

---

## Features

- **Automated Blog Generation:** Unique posts with actionable insights and industry trends.
- **AI-Generated Imagery:** Custom images created by DALL·E with fallback support.
- **Image Processing:** Resizes and compresses images for Bluesky’s file size limits.
- **Multi-Platform Posting:** Automatically posts to Blogger, Bluesky, Twitter, and Twitter Premium.
- **Topic Deduplication:** Tracks past topics to avoid repetition.
- **Logging:** Detailed logs for monitoring and troubleshooting.

---

## Prerequisites

- **Python 3.7+**
- Required libraries (see [Installation](#installing-dependencies)):
  - `openai`
  - `tweepy`
  - `Pillow`
  - `google-api-python-client`
  - `google-auth`
  - `python-dotenv`
  - `atproto`
  - `requests`
- Valid API credentials for:
  - **OpenAI**
  - **Google Drive** (Service Account)
  - **Blogger**
  - **Bluesky**
  - **Twitter**

---

## Installation

### Creating a Virtual Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/automation-blog-promotion.git
   cd automation-blog-promotion
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate      # Windows
   ```

### Installing Dependencies

Once inside the virtual environment, install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Sample requirements.txt

Create a `requirements.txt` file in the project root and add the following:
   ```
   openai
   tweepy
   pillow
   google-api-python-client
   google-auth
   python-dotenv
   atproto
   requests
   ```

---

## Configuration

### .env File Setup

Create a `.env` file **outside** of the project directory (for security) and populate it with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/google_service_account.json
   BLOGGER_CREDENTIALS_FILE=/absolute/path/to/blogger_credentials.json
   BLOGGER_TOKEN_FILE=/absolute/path/to/blogger_token.json
   BLOGGER_BLOG_ID=your_blogger_blog_id
   BSKY_HANDLE=your_bluesky_handle
   BSKY_PASSWORD=your_bluesky_password
   TWITTER_API_KEY=your_twitter_api_key
   TWITTER_API_SECRET=your_twitter_api_secret
   TWITTER_ACCESS_TOKEN=your_twitter_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
   ```

### Directory Setup

Ensure the following directory structure exists:
   ```
   automation-blog-promotion/
   │-- main.py
   │-- requirements.txt
   │-- logs/
   │   │-- script_log.txt
   │-- media/
   │   │-- fallback_images/
   │-- venv/  (Virtual environment)
   ```

**Credentials (Stored Outside the Project Folder):**
   ```
   /path/to/credentials/
   │-- google_service_account.json
   │-- blogger_credentials.json
   ```

---

## Usage

To generate a blog post and promote it, run:
   ```bash
   python main.py
   ```

This will:
1. Generate a unique blog topic and content.
2. Create an AI-generated image or use a fallback image.
3. Upload the image to Google Drive.
4. Post the blog to Blogger.
5. Post promotional messages to Bluesky and Twitter.

---

## Cron Job Setup

To automate the script execution, add a cron job:
   ```bash
   crontab -e
   ```
Then add:
   ```
   0 8 * * 1-5 /bin/bash -c 'sleep $((RANDOM % 14400)); /path/to/venv/bin/python /path/to/automation-blog-promotion/main.py >> /path/to/logs/script_log.txt 2>&1'
   ```
This runs the script at a **random time between 8 AM and 12 PM** on weekdays.

---

## Troubleshooting

### Common Issues and Fixes

#### OpenAI API Errors
**Error:** `openai.OpenAIError: Invalid API key`
**Solution:** Ensure your API key is correct and added to `.env`.

#### Blogger Authentication Fails
**Error:** `Blogger authentication failed`
**Solution:** Re-authenticate your Blogger credentials using Google OAuth.

#### Bluesky Post Not Appearing
**Error:** `Bluesky API response: Error posting`
**Solution:** Ensure your Bluesky credentials are correct in `.env`.

#### Twitter API Fails
**Error:** `Twitter API Error: TweepyException`
**Solution:** Ensure Twitter API credentials are set correctly in `.env`.

#### rsync Backup Failing
**Error:** `rsync: No such file or directory (2)`
**Solution:** Ensure the backup directory exists before running `rsync`.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

For support or inquiries, contact [tim@timgabaree.com](mailto:fb8e5434d0e94cc1a7a99e6dccf4e971@domainsbyproxy.com).
```

