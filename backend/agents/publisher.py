"""Publisher Agent for ThookAI.

Handles publishing content to connected social media platforms:
- LinkedIn
- X/Twitter
- Instagram
"""
import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)


async def get_platform_token(user_id: str, platform: str) -> Optional[str]:
    """Import and call the token getter from platforms route."""
    from routes.platforms import get_platform_token as _get_token
    return await _get_token(user_id, platform)


# ============ LINKEDIN PUBLISHER ============

async def publish_to_linkedin(
    user_id: str,
    content: str,
    media_assets: Optional[List[Dict[str, Any]]] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish content to LinkedIn.

    Args:
        user_id: User ID
        content: Text content to post
        media_assets: Optional list of images/media
        token: Pre-fetched access token (skips DB lookup if provided)

    Returns:
        {success, post_id, post_url, error}
    """
    access_token = token or await get_platform_token(user_id, "linkedin")
    if not access_token:
        return {"success": False, "error": "LinkedIn not connected or token expired"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Get user's LinkedIn URN
            profile_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15.0
            )
            
            if profile_response.status_code != 200:
                return {"success": False, "error": "Failed to get LinkedIn profile"}
            
            profile = profile_response.json()
            person_urn = f"urn:li:person:{profile.get('sub')}"
            
            # Prepare post payload
            post_payload = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content[:3000]  # LinkedIn limit
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Handle media if present (simplified - text only for MVP)
            # Full media upload would require separate asset upload
            
            # Create post
            post_response = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json=post_payload,
                timeout=30.0
            )
            
            if post_response.status_code in [200, 201]:
                post_id = post_response.headers.get("x-restli-id", "")
                # LinkedIn post URLs follow this pattern
                post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url,
                    "platform": "linkedin",
                    "published_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                error_detail = post_response.text
                logger.error(f"LinkedIn publish failed: {error_detail}")
                return {"success": False, "error": f"LinkedIn API error: {post_response.status_code}"}
    
    except Exception as e:
        logger.error(f"LinkedIn publish error: {e}")
        return {"success": False, "error": str(e)}


# ============ X/TWITTER PUBLISHER ============

async def publish_to_x(
    user_id: str,
    content: str,
    is_thread: bool = False,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish content to X/Twitter.
    
    Args:
        user_id: User ID
        content: Text content (or thread content with 1/ 2/ markers)
        is_thread: Whether to post as a thread
    
    Returns:
        {success, tweet_ids, tweet_urls, error}
    """
    access_token = token or await get_platform_token(user_id, "x")
    if not access_token:
        return {"success": False, "error": "X not connected or token expired"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Parse thread if needed
            if is_thread or "1/" in content or "1)" in content:
                tweets = _parse_thread(content)
            else:
                tweets = [content[:280]]  # Single tweet, truncate to limit
            
            tweet_ids = []
            tweet_urls = []
            reply_to = None
            
            for i, tweet_text in enumerate(tweets):
                payload = {"text": tweet_text[:280]}
                
                # If this is a reply in a thread
                if reply_to:
                    payload["reply"] = {"in_reply_to_tweet_id": reply_to}
                
                response = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    tweet_id = data.get("data", {}).get("id")
                    tweet_ids.append(tweet_id)
                    tweet_urls.append(f"https://twitter.com/i/status/{tweet_id}")
                    reply_to = tweet_id  # Next tweet replies to this one
                else:
                    logger.error(f"X publish failed for tweet {i+1}: {response.text}")
                    if i == 0:
                        return {"success": False, "error": f"X API error: {response.status_code}"}
                    break
                
                # Small delay between thread tweets
                if i < len(tweets) - 1:
                    await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "tweet_ids": tweet_ids,
                "tweet_urls": tweet_urls,
                "post_url": tweet_urls[0] if tweet_urls else None,
                "platform": "x",
                "is_thread": len(tweet_ids) > 1,
                "published_at": datetime.now(timezone.utc).isoformat()
            }
    
    except Exception as e:
        logger.error(f"X publish error: {e}")
        return {"success": False, "error": str(e)}


def _parse_thread(content: str) -> List[str]:
    """Parse thread content into individual tweets."""
    import re
    
    # Try to split by numbered patterns like "1/" or "1)"
    pattern = r'(?:^|\n)(?:\d+[\/\)])\s*'
    parts = re.split(pattern, content)
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) > 1:
        return parts
    
    # Fallback: split by double newlines if content is long
    if len(content) > 280:
        paragraphs = content.split('\n\n')
        tweets = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= 280:
                current = f"{current}\n\n{p}".strip() if current else p
            else:
                if current:
                    tweets.append(current)
                current = p
        if current:
            tweets.append(current)
        return tweets if len(tweets) > 1 else [content[:280]]
    
    return [content[:280]]


# ============ INSTAGRAM PUBLISHER ============

async def publish_to_instagram(
    user_id: str,
    caption: str,
    image_url: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish content to Instagram.
    
    Note: Instagram requires a media (image/video) for posts.
    
    Args:
        user_id: User ID
        caption: Caption text
        image_url: URL of image to post (required)
    
    Returns:
        {success, post_id, post_url, error}
    """
    from database import db
    
    access_token = token or await get_platform_token(user_id, "instagram")
    if not access_token:
        return {"success": False, "error": "Instagram not connected or token expired"}
    
    # Get Instagram account ID
    token_doc = await db.platform_tokens.find_one({
        "user_id": user_id,
        "platform": "instagram"
    })
    
    if not token_doc or not token_doc.get("instagram_account_id"):
        return {"success": False, "error": "Instagram business account not found. Please reconnect."}
    
    ig_account_id = token_doc["instagram_account_id"]
    
    if not image_url:
        return {"success": False, "error": "Instagram requires an image. Generate one first."}
    
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            container_response = await client.post(
                f"https://graph.facebook.com/v18.0/{ig_account_id}/media",
                params={
                    "image_url": image_url,
                    "caption": caption[:2200],  # Instagram limit
                    "access_token": access_token
                },
                timeout=60.0
            )
            
            if container_response.status_code != 200:
                logger.error(f"Instagram container creation failed: {container_response.text}")
                return {"success": False, "error": "Failed to create Instagram media container"}
            
            container_data = container_response.json()
            container_id = container_data.get("id")
            
            if not container_id:
                return {"success": False, "error": "No container ID returned"}
            
            # Step 2: Wait for container to be ready (Instagram processes the media)
            for _ in range(30):  # Max 30 attempts
                status_response = await client.get(
                    f"https://graph.facebook.com/v18.0/{container_id}",
                    params={
                        "fields": "status_code",
                        "access_token": access_token
                    },
                    timeout=15.0
                )
                
                if status_response.status_code == 200:
                    status = status_response.json().get("status_code")
                    if status == "FINISHED":
                        break
                    elif status == "ERROR":
                        return {"success": False, "error": "Instagram media processing failed"}
                
                await asyncio.sleep(2)
            
            # Step 3: Publish the container
            publish_response = await client.post(
                f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": access_token
                },
                timeout=30.0
            )
            
            if publish_response.status_code == 200:
                publish_data = publish_response.json()
                post_id = publish_data.get("id")
                
                # Get permalink
                permalink_response = await client.get(
                    f"https://graph.facebook.com/v18.0/{post_id}",
                    params={
                        "fields": "permalink",
                        "access_token": access_token
                    },
                    timeout=15.0
                )
                
                post_url = None
                if permalink_response.status_code == 200:
                    post_url = permalink_response.json().get("permalink")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url,
                    "platform": "instagram",
                    "published_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                logger.error(f"Instagram publish failed: {publish_response.text}")
                return {"success": False, "error": "Failed to publish to Instagram"}
    
    except Exception as e:
        logger.error(f"Instagram publish error: {e}")
        return {"success": False, "error": str(e)}


# ============ SINGLE-PLATFORM DISPATCHER ============

async def publish_to_platform(
    platform: str,
    content: str,
    access_token: str,
    user_id: str = None,
    media_assets: list = None,
) -> dict:
    """Dispatch to the appropriate platform-specific publisher.

    This is the entry point used by the scheduled-post publisher in
    ``tasks.content_tasks``.

    When ``access_token`` is provided it is passed directly to the
    platform function, avoiding a redundant database lookup.

    Returns a dict with at least ``{"success": bool}``.
    """
    if platform == "linkedin":
        return await publish_to_linkedin(user_id or "", content, media_assets, token=access_token)
    elif platform in ("x", "twitter"):
        return await publish_to_x(user_id or "", content, token=access_token)
    elif platform == "instagram":
        image_url = None
        if media_assets:
            for asset in media_assets:
                if isinstance(asset, dict) and asset.get("type") == "image":
                    image_url = asset.get("image_url") or asset.get("url")
                    if image_url:
                        break
        return await publish_to_instagram(user_id or "", content, image_url, token=access_token)
    else:
        return {"success": False, "error": f"Unsupported platform: {platform}"}


# ============ UNIFIED PUBLISHER ============

async def publish_content(
    user_id: str,
    content: str,
    platforms: List[str],
    media_assets: Optional[List[Dict[str, Any]]] = None,
    is_thread: bool = False
) -> Dict[str, Any]:
    """Publish content to multiple platforms.
    
    Args:
        user_id: User ID
        content: Content to publish
        platforms: List of platforms ["linkedin", "x", "instagram"]
        media_assets: Optional media
        is_thread: Whether X post is a thread
    
    Returns:
        Results for each platform
    """
    results = {}
    
    for platform in platforms:
        if platform == "linkedin":
            results["linkedin"] = await publish_to_linkedin(user_id, content, media_assets)
        elif platform == "x":
            results["x"] = await publish_to_x(user_id, content, is_thread)
        elif platform == "instagram":
            # Instagram needs an image URL
            image_url = None
            if media_assets:
                for asset in media_assets:
                    if asset.get("type") == "image" and asset.get("image_url"):
                        image_url = asset["image_url"]
                        break
            results["instagram"] = await publish_to_instagram(user_id, content, image_url)
    
    # Summary
    successful = [p for p, r in results.items() if r.get("success")]
    failed = [p for p, r in results.items() if not r.get("success")]
    
    return {
        "results": results,
        "successful_platforms": successful,
        "failed_platforms": failed,
        "all_success": len(failed) == 0,
        "partial_success": len(successful) > 0 and len(failed) > 0
    }
