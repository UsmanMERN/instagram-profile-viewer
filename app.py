import os
import base64
import json
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Union, Optional, Tuple

import pytz
import requests
from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
import time
import random

app = Flask(__name__)

# Instagram Credentials
USERNAME = "your instagram username here"
PASSWORD = "your instagram passoword"
SESSION_FILE = "session.json"

# Custom Jinja2 filter to format large numbers
def format_number(value):
    """Format large numbers with K (thousands) or M (millions)."""
    try:
        value = int(value)
        if value >= 1000000:
            return f"{value / 1000000:.1f}M"
        elif value >= 1000:
            return f"{value / 1000:.1f}K"
        return str(value)
    except (ValueError, TypeError):
        return "0"

# Register the filter with Jinja2
app.jinja_env.filters['format_number'] = format_number

class TimeConverter:
    """Utility class for handling timestamp conversions."""

    @staticmethod
    def convert_unix_timestamp(timestamp: int) -> tuple[str, str]:
        """Convert Unix timestamp to local time in Asia/Kolkata timezone."""
        dt_server = datetime.fromtimestamp(timestamp, tz=pytz.timezone('UTC'))
        dt_local = dt_server.astimezone(pytz.timezone('Asia/Kolkata'))

        formatted_time = dt_local.strftime("%d %B %Y %I:%M %p %A")
        formatted_date = dt_local.strftime("%Y-%m-%d")

        return formatted_time, formatted_date

class InstaClient:
    """Singleton class to manage Instagram client session."""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InstaClient, cls).__new__(cls)
        return cls._instance

    def get_client(self) -> Client:
        """Get or create Instagram client with session management."""
        if self._client is None:
            self._client = Client()
            # Add delay between requests to avoid rate limiting - increased for bot protection
            self._client.delay_range = [3, 8]
            self._login()
        return self._client

    def _login(self):
        """Login to Instagram using session file or credentials."""
        try:
            if os.path.exists(SESSION_FILE):
                try:
                    self._client.load_settings(SESSION_FILE)
                    # Test the session by making a simple API call
                    self._client.account_info()
                    print("Session loaded successfully!")
                    return
                except Exception as e:
                    print(f"Session expired or invalid, logging in again: {e}")
                    os.remove(SESSION_FILE)  # Remove invalid session file
            
            # Fresh login
            self._client.login(USERNAME, PASSWORD)
            self._client.dump_settings(SESSION_FILE)
            print("Logged in and session saved!")
        except Exception as e:
            print(f"Login error: {e}")
            raise e

class InstaStory:
    """Class to handle Instagram profile downloading operations including stories, posts, reels, highlights."""

    def __init__(self, username: Optional[str] = ''):
        """Initialize the InstaStory downloader."""
        self._username = None
        self.username = username
        self.user_id = None
        self.cl = InstaClient().get_client()

    @property
    def username(self):
        """Get the username."""
        return self._username

    @username.setter
    def username(self, username_id):
        """Set the username and call get_profile_name."""
        self._username = self.get_profile_name(username_id)

    def get_profile_name(self, username_id: str) -> str:
        """Extract profile name from profile url."""
        return username_id.split('?')[0].strip('/').split('/')[-1].strip()

    def get_profile_details(self) -> Dict:
        """Get profile details using instagrapi."""
        try:
            user_info = self.cl.user_info_by_username(self.username)
            
            profile_details = {
                "username": self.username,
                "user_id": str(user_info.pk),
                "full_name": user_info.full_name or self.username,
                "posts_count": user_info.media_count,
                "followers": user_info.follower_count,
                "following": user_info.following_count,
                "bio": user_info.biography or '',
                "external_url": user_info.external_url or '',
                "category_name": user_info.category or '',
                "is_private": user_info.is_private,
                "is_verified": user_info.is_verified,
                "profile_pic_url": str(user_info.profile_pic_url_hd),
            }
            return profile_details
        except Exception as e:
            print(f"Failed to fetch profile details for {self.username}: {str(e)}")
            return {"error": f"Failed to fetch profile details: {str(e)}"}

    def story_download(self) -> Dict:
        """Download stories from Instagram and fetch profile details."""
        if not self.validate_inputs():
            return {"error": "Username is Missing!"}

        profile_details = self.get_profile_details()
        if "error" in profile_details:
            return profile_details

        self.user_id = profile_details['user_id']
        profile_pic_content, profile_pic_type = self.get_media_content(profile_details.get('profile_pic_url'), False)

        story_data = self.get_story()
        story_data.update(profile_details)
        story_data['profile_pic_content'] = profile_pic_content
        story_data['profile_pic_type'] = profile_pic_type

        return {self.username: story_data}

    def validate_inputs(self) -> bool:
        """Validate input data."""
        return bool(self.username)

    def get_story(self) -> Dict:
        """Get story data using instagrapi - FIXED VERSION."""
        try:
            user_id = int(self.user_id)
            
            # First try to get stories directly
            try:
                stories = self.cl.user_stories(user_id)
                print(f"Found {len(stories)} stories for user {self.username}")
            except Exception as e:
                print(f"Error fetching stories directly: {e}")
                # Try alternative method - get reel feed
                try:
                    reel_feed = self.cl.reels_media([user_id])
                    stories = reel_feed.get(user_id, {}).get('items', []) if reel_feed else []
                    print(f"Found {len(stories)} stories via reel feed for user {self.username}")
                except Exception as e2:
                    print(f"Error fetching via reel feed: {e2}")
                    stories = []
            
            if not stories:
                return {
                    'url': f'https://www.instagram.com/stories/{self.username}/',
                    'Story Data': []
                }
            
            processed_items = []
            
            # Process stories sequentially to avoid rate limiting
            for idx, story in enumerate(stories, 1):
                try:
                    story_item = self.process_single_story(story, idx)
                    if story_item:
                        processed_items.append(story_item)
                    
                    # Add delay between processing - increased for bot protection
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    print(f"Error processing story {idx}: {e}")
                    continue
            
            return {
                'url': f'https://www.instagram.com/stories/{self.username}/',
                'Story Data': processed_items
            }
        except Exception as e:
            print(f"Error getting story: {e}")
            return {
                'url': f'https://www.instagram.com/stories/{self.username}/',
                'Story Data': []
            }

    def process_single_story(self, story, index) -> Dict:
        """Process a single story item - FIXED VERSION with lazy loading."""
        try:
            # Handle different story object types
            if hasattr(story, 'media_type'):
                is_video = story.media_type == 2
                thumbnail_url = str(story.thumbnail_url)
                video_url = str(story.video_url) if is_video else None
                media_url = video_url if is_video else thumbnail_url
                preview_url = thumbnail_url  # always image for preview
                story_pk = story.pk
                taken_at = story.taken_at.timestamp()
                caption_text = getattr(story, 'caption_text', '')
            else:
                # Handle dict-like story objects from reel feed
                is_video = story.get('media_type') == 2
                image_versions = story.get('image_versions2', {}).get('candidates', [])
                thumbnail_url = image_versions[0].get('url', '') if image_versions else ''
                video_versions = story.get('video_versions', []) if is_video else []
                video_url = video_versions[0].get('url', '') if video_versions else None
                media_url = video_url if is_video else thumbnail_url
                preview_url = thumbnail_url
                story_pk = story.get('pk', story.get('id', ''))
                taken_at = story.get('taken_at', 0)
                caption = story.get('caption')
                caption_text = caption.get('text', '') if caption else ''
            
            if not preview_url:
                print(f"No preview URL found for story {index}")
                return None
            
            preview_content, preview_type = self.get_media_content(preview_url, False)
            
            if not preview_content:
                print(f"Failed to download preview for story {index}")
                return None
            
            preview_base64 = base64.b64encode(preview_content).decode('utf-8')
            
            story_time, _ = TimeConverter.convert_unix_timestamp(int(taken_at))
            ext = 'mp4' if is_video else 'jpg'
            filename = f"{self.username}_story_{story_pk}.{ext}"
            
            # Get story viewers if it's user's own story
            viewers = []
            viewer_count = 0
            try:
                own_user_info = self.cl.account_info()
                if str(own_user_info.pk) == str(self.user_id):
                    story_viewers = self.cl.story_viewers(story_pk, amount=50)
                    viewers = [{"username": viewer.username, "full_name": viewer.full_name} for viewer in story_viewers]
                    viewer_count = len(story_viewers)
            except:
                pass

            return {
                'url': f'https://www.instagram.com/stories/{self.username}/{story_pk}/',
                'Time': story_time,
                'Tag': '',
                'filename': filename,
                'viewers': viewers,
                'viewer_count': viewer_count,
                'caption': caption_text,
                'expiring_at': TimeConverter.convert_unix_timestamp(int(taken_at + 86400))[0],
                'preview_content': preview_base64,
                'preview_type': preview_type,
                'media_url': media_url,
                'is_video': is_video
            }
        except Exception as e:
            print(f"Error processing story {index}: {e}")
            return None

    def get_media_content(self, link: str, is_video: bool) -> Tuple[bytes, str]:
        """Download media and return content bytes and type."""
        try:
            if not link:
                return b'', ''
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(link, timeout=15, headers=headers)
            if response.status_code == 200:
                media_type = 'video/mp4' if is_video else 'image/jpeg'
                return response.content, media_type
        except Exception as e:
            print(f"Error downloading media from {link}: {e}")
        return b'', ''

    def get_posts(self, end_cursor: Optional[str] = None) -> Dict:
        """Fetch recent posts from the profile using instagrapi - FIXED PAGINATION."""
        if not self.user_id:
            return {"posts": [], "next_max_id": None}

        try:
            user_id = int(self.user_id)
            
            # Use the correct paginated method with end_cursor - reduced to 6 for optimization
            medias, next_cursor = self.cl.user_medias_paginated_v1(user_id, amount=6, end_cursor=end_cursor or "")
            
            # Filter out reels/videos - only get images and carousels
            posts = [m for m in medias if m.media_type in [1, 8]]  # 1=photo, 8=carousel
            
            processed = []
            for post in posts[:6]:  # Limit to 6 posts
                try:
                    # Only get metadata first, don't download content yet
                    post_data = self.process_single_post_metadata(post)
                    if post_data:
                        processed.append(post_data)
                    
                    # Add delay between processing posts for bot protection
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    print(f"Error processing post {post.pk}: {e}")
                    continue
            
            return {"posts": processed, "next_max_id": next_cursor}
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return {"posts": [], "next_max_id": None}

    def process_single_post_metadata(self, post) -> Dict:
        """Process a single post metadata only (with preview content download)."""
        try:
            media_list = []
            
            if post.media_type == 8:  # Carousel
                for resource in post.resources:
                    is_video = resource.media_type == 2
                    if is_video:
                        preview_url = resource.thumbnail_url
                        media_url = resource.video_url
                        preview_content, _ = self.get_media_content(str(preview_url), False)
                    else:
                        preview_url = resource.thumbnail_url
                        media_url = preview_url
                        preview_content, _ = self.get_media_content(str(media_url), False)
                    
                    if preview_content:
                        preview_base64 = base64.b64encode(preview_content).decode('utf-8')
                        ext = 'mp4' if is_video else 'jpg'
                        filename = f"{self.username}_post_{resource.pk}.{ext}"
                        media_type = 'video/mp4' if is_video else 'image/jpeg'
                        
                        media_list.append({
                            'filename': filename,
                            'Tag': '',
                            'media_url': str(media_url),
                            'is_video': is_video,
                            'preview_content': preview_base64,
                            'media_type': media_type,
                            'content': None  # Will be loaded on demand
                        })
                        
                        # Delay for each resource in carousel
                        time.sleep(random.uniform(1, 2))
            else:  # Single image
                is_video = post.media_type == 2
                if is_video:
                    preview_url = post.thumbnail_url
                    media_url = post.video_url
                    preview_content, _ = self.get_media_content(str(preview_url), False)
                else:
                    media_url = post.thumbnail_url
                    preview_content, _ = self.get_media_content(str(media_url), False)
                
                if preview_content:
                    preview_base64 = base64.b64encode(preview_content).decode('utf-8')
                    filename = f"{self.username}_post_{post.pk}.jpg" if not is_video else f"{self.username}_post_{post.pk}.mp4"
                    media_list.append({
                        'filename': filename,
                        'Tag': '',
                        'media_url': str(media_url),
                        'is_video': is_video,
                        'preview_content': preview_base64,
                        'media_type': 'image/jpeg' if not is_video else 'video/mp4',
                        'content': None  # Will be loaded on demand
                    })

            if media_list:
                time_str, _ = TimeConverter.convert_unix_timestamp(int(post.taken_at.timestamp()))
                return {
                    'time': time_str,
                    'code': post.code,
                    'caption': post.caption_text or '',
                    'like_count': post.like_count,
                    'comment_count': post.comment_count,
                    'media_data': media_list
                }
        except Exception as e:
            print(f"Error processing post: {e}")
        return None

    def get_reels(self, end_cursor: Optional[str] = None) -> Dict:
        """Fetch recent reels from the profile using instagrapi - FIXED PAGINATION."""
        if not self.user_id:
            return {"reels": [], "next_max_id": None}

        try:
            user_id = int(self.user_id)
            
            # Use the correct paginated method with end_cursor - reduced to 6 for optimization
            clips, next_cursor = self.cl.user_clips_paginated_v1(user_id, amount=6, end_cursor=end_cursor or "")
            
            processed = []
            for clip in clips[:6]:  # Limit to 6 reels
                try:
                    # Only get metadata first, don't download content yet
                    reel_data = self.process_single_reel_metadata(clip)
                    if reel_data:
                        processed.append(reel_data)
                    
                    # Add delay between processing reels for bot protection
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    print(f"Error processing reel {clip.pk}: {e}")
                    continue
            
            return {"reels": processed, "next_max_id": next_cursor}
        except Exception as e:
            print(f"Error fetching reels: {e}")
            return {"reels": [], "next_max_id": None}

    def process_single_reel_metadata(self, reel) -> Dict:
        """Process a single reel metadata only (with preview content download)."""
        try:
            if not reel.video_url:
                return None
            
            # Download preview content
            preview_content, _ = self.get_media_content(str(reel.thumbnail_url), False)
            preview_base64 = base64.b64encode(preview_content).decode('utf-8') if preview_content else ''
            
            filename = f"{self.username}_reel_{reel.pk}.mp4"
            time_str, _ = TimeConverter.convert_unix_timestamp(int(reel.taken_at.timestamp()))
            
            return {
                'time': time_str,
                'code': reel.code,
                'caption': reel.caption_text or '',
                'like_count': reel.like_count,
                'comment_count': reel.comment_count,
                'play_count': getattr(reel, 'play_count', 0),
                'view_count': getattr(reel, 'view_count', 0),
                'media_data': [{
                    'filename': filename,
                    'Tag': '',
                    'media_url': str(reel.video_url),
                    'is_video': True,
                    'preview_content': preview_base64,
                    'media_type': 'video/mp4',
                    'content': None  # Will be loaded on demand
                }]
            }
        except Exception as e:
            print(f"Error processing reel: {e}")
        return None

    def get_highlights(self) -> List:
        """Fetch highlights list from the profile (only metadata, no items) using instagrapi."""
        if not self.user_id:
            return []
        
        try:
            user_id = int(self.user_id)
            
            # Get highlights list first
            highlights = self.cl.user_highlights(user_id)
            print(f"Found {len(highlights)} highlights for user {self.username}")
            
            if not highlights:
                return []
            
            processed_highlights = []
            
            for highlight in highlights:
                try:
                    print(f"Processing highlight metadata: {highlight.title}")
                    
                    # === FIX START: Highly robust URL extraction ===
                    cover_url = ''
                    if highlight.cover_media:
                        # Path 1: Standard object attribute access (most common)
                        try:
                            cover_url = str(highlight.cover_media.cropped_image_version.url)
                        except (AttributeError, TypeError):
                            # Path 2: Dictionary key access (handles logs provided)
                            if isinstance(highlight.cover_media, dict):
                                cropped_version = highlight.cover_media.get('cropped_image_version')
                                if isinstance(cropped_version, dict):
                                    cover_url = cropped_version.get('url')

                        # Path 3: Fallback structure (image_versions2)
                        if not cover_url:
                            try:
                                cover_url = str(highlight.cover_media.image_versions2.candidates[0].url)
                            except (AttributeError, IndexError, TypeError):
                                if isinstance(highlight.cover_media, dict):
                                    image_versions = highlight.cover_media.get('image_versions2', {})
                                    candidates = image_versions.get('candidates', [])
                                    if candidates and isinstance(candidates[0], dict):
                                        cover_url = candidates[0].get('url')
                    # === FIX END ===

                    print(f"Highlight cover URL: {cover_url}")
                    # Download cover content for base64
                    cover_content, cover_type = self.get_media_content(cover_url, False)
                    if not cover_content:
                        # This log will now only appear if the extracted URL is empty or invalid
                        print(f"Failed to download cover for highlight {highlight.pk}")
                    cover_base64 = base64.b64encode(cover_content).decode('utf-8') if cover_content else ''
                    
                    processed_highlights.append({
                        'id': str(highlight.pk),
                        'title': highlight.title,
                        'cover_base64': cover_base64,
                        'cover_type': cover_type
                    })
                    
                    # Add delay between highlights for bot protection - increased
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"Error processing highlight metadata {highlight.pk}: {e}")
                    continue
            
            return processed_highlights
        except Exception as e:
            print(f"Error fetching highlights: {e}")
            return []

    def get_highlight_items(self, highlight_id: str) -> List:
        """Fetch items for a specific highlight on demand."""
        if not self.user_id:
            return []
        
        try:
            # Get highlight details and items
            highlight_info = self.cl.highlight_info(highlight_id)
            
            if not highlight_info or not highlight_info.items:
                print(f"No items found for highlight {highlight_id}")
                return []
            
            story_data = []
            
            # Process each story item in the highlight
            for item in highlight_info.items:
                try:
                    is_video = item.media_type == 2
                    media_url = item.video_url if is_video else item.thumbnail_url
                    
                    if not media_url:
                        continue
                        
                    content, media_type = self.get_media_content(str(media_url), is_video)
                    
                    if content:
                        story_time, _ = TimeConverter.convert_unix_timestamp(int(item.taken_at.timestamp()))
                        ext = 'mp4' if is_video else 'jpg'
                        filename = f"{self.username}_highlight_{item.pk}.{ext}"
                        story_data.append({
                            'content': base64.b64encode(content).decode('utf-8'),
                            'media_type': media_type,
                            'filename': filename,
                            'Time': story_time
                        })
                    
                    # Add delay between items for bot protection - increased
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    print(f"Error processing highlight item {item.pk}: {e}")
                    continue
            
            print(f"Successfully processed {len(story_data)} items for highlight {highlight_id}")
            return story_data
        except Exception as e:
            print(f"Error fetching highlight items {highlight_id}: {e}")
            return []

class InstaPost:
    """Class to handle Instagram post/reel downloading operations using instagrapi."""

    def __init__(self, media_id: Optional[str] = ''):
        """Initialize the InstaPost downloader."""
        self._media_code = None
        self.media_code = media_id
        self.username = 'unknown'
        self.cl = InstaClient().get_client()

    @property
    def media_code(self):
        """Get the media_code."""
        return self._media_code

    @media_code.setter
    def media_code(self, media_id):
        """Set the media_code and call get_media_slug."""
        self._media_code = self.get_media_slug(media_id)

    def get_media_slug(self, media_id: str) -> str:
        """Extract media slug from post/reel url."""
        return media_id.split('?')[0].strip('/').split('/')[-1].strip()

    def media_download(self) -> Dict:
        """Main function to download post or reel using instagrapi with lazy loading."""
        if not self.validate_inputs():
            return {"error": "Post ID is missing!"}
        
        try:
            # *** FIX START: Correct way to fetch media by shortcode ***
            # Construct the full URL from the shortcode
            media_url = f"https://www.instagram.com/p/{self.media_code}/"
            # Get the media's primary key (pk) from the URL
            media_pk = self.cl.media_pk_from_url(media_url)
            # Fetch the media information using its pk
            media = self.cl.media_info(media_pk)
            # *** FIX END ***

            self.username = media.user.username
            
            profile_pic_content, profile_pic_type = self.get_media_content(str(media.user.profile_pic_url_hd), False)
            time_str, _ = TimeConverter.convert_unix_timestamp(int(media.taken_at.timestamp()))
            
            # Fetch metadata and previews only, not full content
            media_list = self.process_media_items_metadata_instagrapi(media)
            
            return {
                self.username: {
                    'url': f"https://www.instagram.com/p/{media.code}/",
                    'caption': media.caption_text or '',
                    'profile_pic_content': profile_pic_content,
                    'profile_pic_type': profile_pic_type,
                    'time': time_str,
                    'like_count': media.like_count,
                    'comment_count': media.comment_count,
                    'play_count': media.play_count if hasattr(media, 'play_count') else 0,
                    'media_data': media_list
                }
            }
        except Exception as e:
            print(f"Media download error: {e}")
            return {"error": f"Post not found or error occurred: {str(e)}"}

    def validate_inputs(self) -> bool:
        """Validate input data."""
        return bool(self.media_code)

    def get_media_content(self, link: str, is_video: bool) -> Tuple[bytes, str]:
        """Download media file and return content bytes and type."""
        try:
            if not link:
                return b'', ''
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(link, timeout=15, headers=headers)
            if response.status_code == 200:
                media_type = 'video/mp4' if is_video else 'image/jpeg'
                return response.content, media_type
        except Exception as e:
            print(f"Error downloading media: {e}")
        return b'', ''

    def process_media_items_metadata_instagrapi(self, media) -> List:
        """Process media items to get metadata and preview content for lazy loading."""
        processed_media = []
        try:
            if hasattr(media, 'resources') and media.resources:
                # Carousel post
                for resource in media.resources:
                    is_video = resource.media_type == 2
                    if is_video:
                        preview_url = resource.thumbnail_url
                        media_url = resource.video_url
                    else:
                        preview_url = resource.thumbnail_url
                        media_url = preview_url
                    
                    preview_content, _ = self.get_media_content(str(preview_url), False)
                    
                    if preview_content:
                        preview_base64 = base64.b64encode(preview_content).decode('utf-8')
                        ext = 'mp4' if is_video else 'jpg'
                        filename = f"{self.username}_post_{resource.pk}.{ext}"
                        media_type = 'video/mp4' if is_video else 'image/jpeg'
                        
                        processed_media.append({
                            'filename': filename,
                            'Tag': '',
                            'media_url': str(media_url),
                            'is_video': is_video,
                            'preview_content': preview_base64,
                            'media_type': media_type,
                            'content': None  # Set to None for lazy loading
                        })
            else:
                # Single media post or reel
                is_video = media.media_type == 2
                if is_video:
                    preview_url = media.thumbnail_url
                    media_url = media.video_url
                else:
                    preview_url = media.thumbnail_url
                    media_url = preview_url

                preview_content, _ = self.get_media_content(str(preview_url), False)
                
                if preview_content:
                    preview_base64 = base64.b64encode(preview_content).decode('utf-8')
                    ext = 'mp4' if is_video else 'jpg'
                    media_type_str = 'reel' if hasattr(media, 'product_type') and media.product_type == 'clips' else 'post'
                    filename = f"{self.username}_{media_type_str}_{media.pk}.{ext}"
                    media_type = 'video/mp4' if is_video else 'image/jpeg'

                    processed_media.append({
                        'filename': filename,
                        'Tag': '',
                        'media_url': str(media_url),
                        'is_video': is_video,
                        'preview_content': preview_base64,
                        'media_type': media_type,
                        'content': None  # Set to None for lazy loading
                    })
        except Exception as e:
            print(f"Error processing media items metadata: {e}")
        
        return processed_media

# Flask routes

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html", active_tab='story')

@app.route('/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is missing"}), 400

    insta = InstaStory(username=username)
    profile_details = insta.get_profile_details()
    if "error" in profile_details:
        return jsonify(profile_details), 500

    insta.user_id = profile_details['user_id']
    profile_pic_content, profile_pic_type = insta.get_media_content(profile_details.get('profile_pic_url'), False)
    profile_details['profile_pic_base64'] = base64.b64encode(profile_pic_content).decode('utf-8') if profile_pic_content else None
    profile_details['profile_pic_type'] = profile_pic_type

    return jsonify(profile_details)

@app.route('/stories', methods=['GET'])
def get_stories():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    if not username or not user_id:
        return jsonify({"error": "Missing parameters"}), 400

    insta = InstaStory(username=username)
    insta.user_id = user_id
    story_data = insta.get_story()
    return jsonify(story_data)

@app.route('/download_story', methods=['POST'])
def download_story():
    username = request.form.get('username')
    try:
        story_obj = InstaStory(username=username)
        result = story_obj.story_download()

        if 'error' in result:
            return render_template("index.html", error=result['error'], active_tab='story')

        username_key = list(result.keys())[0]
        data = result[username_key]

        profile_pic_base64 = base64.b64encode(data['profile_pic_content']).decode(
            'utf-8') if data['profile_pic_content'] else None

        story_data = data['Story Data']

        story_result = {
            'username': username_key,
            'user_id': data.get('user_id'),
            'full_name': data.get('full_name', username_key),
            'posts_count': data.get('posts_count', 0),
            'followers': data.get('followers', 0),
            'following': data.get('following', 0),
            'bio': data.get('bio', ''),
            'external_url': data.get('external_url', ''),
            'category_name': data.get('category_name', ''),
            'is_private': data.get('is_private', False),
            'is_verified': data.get('is_verified', False),
            'profile_pic_base64': profile_pic_base64,
            'profile_pic_type': data['profile_pic_type'],
            'story_data': story_data,
        }

        return render_template("index.html", story_result=story_result, active_tab='story')

    except Exception as e:
        print(f"Story download error: {e}")
        return render_template("index.html", error=str(e), active_tab='story')

@app.route('/download_post', methods=['POST'])
def download_post():
    post_url = request.form.get('post_url')
    try:
        post_obj = InstaPost(media_id=post_url)
        result = post_obj.media_download()

        if 'error' in result:
            return render_template("index.html", error=result['error'], active_tab='post')
        
        username_key = list(result.keys())[0]
        post_data = result[username_key]

        # Since we are now lazy loading, the initial profile pic is handled
        profile_pic_base64 = base64.b64encode(post_data['profile_pic_content']).decode(
            'utf-8') if post_data['profile_pic_content'] else None

        post_result = {
            'username': username_key,
            'url': post_data.get('url'),
            'caption': post_data.get('caption'),
            'profile_pic_base64': profile_pic_base64,
            'profile_pic_type': post_data.get('profile_pic_type'),
            'time': post_data.get('time'),
            'like_count': post_data.get('like_count'),
            'comment_count': post_data.get('comment_count'),
            'play_count': post_data.get('play_count', 0),
            'media_data': post_data.get('media_data')
        }
        
        return render_template("index.html", post_result=post_result, active_tab='post')

    except Exception as e:
        print(f"Post download error: {e}")
        return render_template("index.html", error=str(e), active_tab='post')

# API endpoints for dynamic content loading

@app.route('/get_posts', methods=['GET'])
def get_user_posts():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    end_cursor = request.args.get('max_id')  # Frontend still sends max_id, but we'll use it as end_cursor

    if not username or not user_id:
        return jsonify({"error": "Username or User ID is missing"}), 400

    insta = InstaStory(username=username)
    insta.user_id = user_id
    posts_data = insta.get_posts(end_cursor=end_cursor)
    return jsonify(posts_data)

@app.route('/get_reels', methods=['GET'])
def get_user_reels():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    end_cursor = request.args.get('max_id')  # Frontend still sends max_id, but we'll use it as end_cursor

    if not username or not user_id:
        return jsonify({"error": "Username or User ID is missing"}), 400

    insta = InstaStory(username=username)
    insta.user_id = user_id
    reels_data = insta.get_reels(end_cursor=end_cursor)
    return jsonify(reels_data)

@app.route('/get_highlights', methods=['GET'])
def get_user_highlights():
    username = request.args.get('username')
    user_id = request.args.get('user_id')

    if not username or not user_id:
        return jsonify({"error": "Username or User ID is missing"}), 400

    insta = InstaStory(username=username)
    insta.user_id = user_id
    highlights_data = insta.get_highlights()
    return jsonify({"highlights": highlights_data})

@app.route('/get_highlight_items', methods=['GET'])
def get_highlight_items():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    highlight_id = request.args.get('highlight_id')

    if not all([username, user_id, highlight_id]):
        return jsonify({"error": "Missing parameters"}), 400

    insta = InstaStory(username=username)
    insta.user_id = user_id
    items = insta.get_highlight_items(highlight_id)
    return jsonify({"story_data": items})  # Changed key to story_data for consistency

# New endpoint to download media content on demand
@app.route('/download_media_content', methods=['POST'])
def download_media_content():
    """Download media content on demand for lazy loading."""
    try:
        data = request.get_json()
        media_url = data.get('media_url')
        is_video = data.get('is_video', False)

        if not media_url:
            return jsonify({"error": "Media URL is required"}), 400
        
        # Create a temporary InstaStory instance to use the download method
        temp_instance = InstaStory()
        content, media_type = temp_instance.get_media_content(media_url, is_video)
        
        if content:
            return jsonify({
                "content": base64.b64encode(content).decode('utf-8'),
                "media_type": media_type
            })
        else:
            return jsonify({"error": "Failed to download media"}), 500
            
    except Exception as e:
        print(f"Error downloading media content: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=False)