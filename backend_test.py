#!/usr/bin/env python3
"""
Backend Testing Suite for ThookAI Sprint 6
Tests Media Agents (Image Generation, Voice Narration), Content Regeneration, and existing functionality
"""

import asyncio
import requests
import json
import time
import sys
import os

# Get backend URL from frontend env
FRONTEND_ENV_PATH = "/app/frontend/.env"
BACKEND_URL = None

try:
    with open(FRONTEND_ENV_PATH, "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BACKEND_URL = line.split("=", 1)[1].strip()
                break
except Exception as e:
    print(f"Error reading frontend .env: {e}")
    sys.exit(1)

if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

API_BASE = f"{BACKEND_URL}/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.job_ids = []
        # Use timestamp to ensure unique email
        import time
        timestamp = int(time.time())
        self.test_email = f"sprint6test{timestamp}@example.com"
        self.test_password = "test123"
        self.test_name = "Sprint 6 Tester"
        
    def log(self, message, level="INFO"):
        print(f"[{level}] {message}")
        
    def test_api_call(self, method, endpoint, data=None, headers=None, timeout=30):
        """Make API call and return response with error handling."""
        try:
            url = f"{API_BASE}{endpoint}"
            default_headers = {"Content-Type": "application/json"}
            if self.token:
                default_headers["Authorization"] = f"Bearer {self.token}"
            if headers:
                default_headers.update(headers)
                
            self.log(f"{method} {url}")
            
            if method == "GET":
                response = requests.get(url, headers=default_headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=default_headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log(f"Response: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.status_code, response.json()
            else:
                return response.status_code, response.text
                
        except Exception as e:
            self.log(f"API call failed: {e}", "ERROR")
            return None, str(e)
    
    async def test_auth_flow(self):
        """Test user registration and authentication."""
        self.log("=== Testing Authentication Flow ===")
        
        # Register new user
        register_data = {
            "email": self.test_email,
            "password": self.test_password,
            "name": self.test_name
        }
        
        status, response = self.test_api_call("POST", "/auth/register", register_data)
        
        if status == 200:
            if isinstance(response, dict) and "token" in response:
                self.token = response["token"]
                self.user_id = response.get("user_id")
                self.log("✅ User registration successful")
                return True
            else:
                self.log("❌ Registration response missing token", "ERROR")
                return False
        elif status == 400 and "already exists" in str(response):
            # Try logging in instead
            self.log("User already exists, trying login...")
            login_data = {
                "email": self.test_email,
                "password": self.test_password
            }
            status, response = self.test_api_call("POST", "/auth/login", login_data)
            
            if status == 200 and isinstance(response, dict) and "token" in response:
                self.token = response["token"]
                self.user_id = response.get("user_id")
                self.log("✅ User login successful")
                return True
            else:
                self.log("❌ Login failed after registration conflict", "ERROR")
                return False
        else:
            self.log(f"❌ Registration failed: {response}", "ERROR")
            return False

    # ============ SPRINT 6 TESTS ============
    
    async def test_image_styles_endpoint(self):
        """Test GET /api/content/image-styles - should return 4 styles."""
        self.log("=== Testing Image Styles Endpoint ===")
        
        status, response = self.test_api_call("GET", "/content/image-styles")
        
        if status == 200:
            if not isinstance(response, dict) or "styles" not in response:
                self.log("❌ Response should contain 'styles' key", "ERROR")
                return False
            
            styles = response["styles"]
            if not isinstance(styles, list):
                self.log("❌ Styles should be a list", "ERROR")
                return False
            
            if len(styles) != 4:
                self.log(f"❌ Expected 4 styles, got {len(styles)}", "ERROR")
                return False
            
            expected_style_ids = ["minimal", "bold", "data-viz", "personal"]
            actual_style_ids = [style.get("id") for style in styles]
            
            missing_styles = [sid for sid in expected_style_ids if sid not in actual_style_ids]
            if missing_styles:
                self.log(f"❌ Missing style IDs: {missing_styles}", "ERROR")
                return False
            
            # Check style structure
            for style in styles:
                if not all(key in style for key in ["id", "name", "description"]):
                    self.log("❌ Each style should have id, name, description", "ERROR")
                    return False
            
            self.log("✅ Image Styles endpoint working correctly")
            self.log(f"Available styles: {actual_style_ids}")
            return True
        else:
            self.log(f"❌ Image Styles endpoint failed: {response}", "ERROR")
            return False
    
    async def test_voices_endpoint(self):
        """Test GET /api/content/voices - should return default voices with Rachel, Domi, etc."""
        self.log("=== Testing Voices Endpoint ===")
        
        status, response = self.test_api_call("GET", "/content/voices")
        
        if status == 200:
            if not isinstance(response, dict):
                self.log("❌ Response should be a dict", "ERROR")
                return False
            
            if "default_voices" not in response:
                self.log("❌ Response should contain 'default_voices'", "ERROR")
                return False
            
            default_voices = response["default_voices"]
            if not isinstance(default_voices, list):
                self.log("❌ default_voices should be a list", "ERROR")
                return False
            
            if len(default_voices) == 0:
                self.log("❌ Should have at least one default voice", "ERROR")
                return False
            
            # Check for expected voices
            voice_names = [voice.get("name", "").lower() for voice in default_voices]
            expected_voices = ["rachel", "domi"]  # At least these should be present
            
            missing_voices = [name for name in expected_voices if name not in voice_names]
            if missing_voices:
                self.log(f"❌ Missing expected voices: {missing_voices}", "ERROR")
                return False
            
            # Check voice structure
            for voice in default_voices[:2]:  # Check first 2 voices
                if not all(key in voice for key in ["id", "name", "description"]):
                    self.log("❌ Each voice should have id, name, description", "ERROR")
                    return False
            
            self.log("✅ Voices endpoint working correctly")
            self.log(f"Found {len(default_voices)} default voices: {[v.get('name') for v in default_voices[:3]]}")
            return True
        else:
            self.log(f"❌ Voices endpoint failed: {response}", "ERROR")
            return False
    
    async def test_content_regeneration_flow(self):
        """Test full content regeneration flow with version tracking."""
        self.log("=== Testing Content Regeneration Flow ===")
        
        # First create content
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "The future of artificial intelligence in creative industries looks promising with innovative tools emerging."
        }
        
        status, response = self.test_api_call("POST", "/content/create", content_data)
        
        if status != 200 or "job_id" not in response:
            self.log("❌ Failed to create initial content for regeneration test", "ERROR")
            return None
        
        original_job_id = response["job_id"]
        self.job_ids.append(original_job_id)
        self.log(f"Created original job: {original_job_id}")
        
        # Poll until ready
        if not await self.poll_job_until_ready(original_job_id):
            self.log("❌ Original job failed to complete", "ERROR")
            return None
        
        # Now test regeneration
        regen_data = {
            "hint": "Make it more engaging and add a personal touch"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{original_job_id}/regenerate", regen_data)
        
        if status != 200:
            self.log(f"❌ Regeneration failed: {response}", "ERROR")
            return None
        
        if not isinstance(response, dict) or "job_id" not in response:
            self.log("❌ Regeneration response should contain new job_id", "ERROR")
            return None
        
        new_job_id = response["job_id"]
        version = response.get("version", 0)
        parent_job_id = response.get("parent_job_id")
        
        if version != 2:
            self.log(f"❌ Expected version 2, got {version}", "ERROR")
            return None
        
        if parent_job_id != original_job_id:
            self.log(f"❌ Expected parent_job_id to be {original_job_id}, got {parent_job_id}", "ERROR")
            return None
        
        self.job_ids.append(new_job_id)
        self.log(f"✅ Regeneration successful: new job {new_job_id}, version {version}")
        
        # Wait for regenerated content to complete
        if not await self.poll_job_until_ready(new_job_id):
            self.log("❌ Regenerated job failed to complete", "ERROR")
            return None
        
        return {"original_job_id": original_job_id, "new_job_id": new_job_id}
    
    async def test_job_history_endpoint(self, job_ids_dict):
        """Test GET /api/content/job/{job_id}/history."""
        if not job_ids_dict:
            self.log("❌ No job IDs available for history test", "ERROR")
            return False
        
        self.log("=== Testing Job History Endpoint ===")
        
        original_job_id = job_ids_dict["original_job_id"]
        
        status, response = self.test_api_call("GET", f"/content/job/{original_job_id}/history")
        
        if status != 200:
            self.log(f"❌ Job history failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ History response should be a dict", "ERROR")
            return False
        
        required_fields = ["root_job_id", "versions", "total_versions"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in history response: {missing_fields}", "ERROR")
            return False
        
        versions = response["versions"]
        if not isinstance(versions, list):
            self.log("❌ Versions should be a list", "ERROR")
            return False
        
        if len(versions) < 2:
            self.log(f"❌ Expected at least 2 versions after regeneration, got {len(versions)}", "ERROR")
            return False
        
        # Check version structure - original jobs may not have version field
        for version in versions:
            required_fields = ["job_id", "status", "created_at"]
            missing_fields = [field for field in required_fields if field not in version]
            if missing_fields:
                self.log(f"❌ Version missing required fields: {missing_fields}", "ERROR")
                return False
        
        # Check that we have at least one regenerated version (should have version field)
        versioned_jobs = [v for v in versions if "version" in v]
        if len(versioned_jobs) == 0:
            self.log("❌ Should have at least one job with version field after regeneration", "ERROR")
            return False
        
        # Check that regenerated job has version 2
        regen_versions = [v.get("version") for v in versioned_jobs if v.get("version")]
        if 2 not in regen_versions:
            self.log(f"❌ Should have regenerated job with version 2, found: {regen_versions}", "ERROR") 
            return False
        
        self.log("✅ Job History endpoint working correctly")
        self.log(f"Found {len(versions)} versions, regenerated versions: {regen_versions}")
        return True
    
    async def test_image_generation(self):
        """Test POST /api/content/generate-image with extended timeout."""
        self.log("=== Testing Image Generation (90s timeout) ===")
        
        # Try to use an existing completed job first
        existing_job_id = None
        if self.job_ids:
            for job_id in self.job_ids:
                status, response = self.test_api_call("GET", f"/content/job/{job_id}")
                if status == 200 and response.get("status") == "reviewing":
                    existing_job_id = job_id
                    self.log(f"Using existing completed job: {job_id}")
                    break
        
        if not existing_job_id:
            # Create a new job only if needed
            content_data = {
                "platform": "linkedin", 
                "content_type": "post",
                "raw_input": "Visual representation of sustainable technology."
            }
            
            status, response = self.test_api_call("POST", "/content/create", content_data)
            
            if status != 200 or "job_id" not in response:
                self.log("❌ Failed to create job for image generation test", "ERROR")
                return False
            
            existing_job_id = response["job_id"]
            self.job_ids.append(existing_job_id)
            
            # Wait for job to complete with shorter timeout
            if not await self.poll_job_until_ready(existing_job_id, max_wait=30):
                self.log("❌ Job failed to complete quickly, testing with partial job", "ERROR")
                # Continue with test anyway - the image generation endpoint should handle this
        
        # Test image generation
        image_data = {
            "job_id": existing_job_id,
            "style": "minimal"
        }
        
        # Use extended timeout for image generation (90 seconds as requested)
        status, response = self.test_api_call("POST", "/content/generate-image", image_data, timeout=90)
        
        if status != 200:
            self.log(f"❌ Image generation failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Image generation response should be a dict", "ERROR")
            return False
        
        # Check response structure - both real and mock responses are acceptable
        expected_fields = ["generated", "style"]
        missing_fields = [field for field in expected_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in image response: {missing_fields}", "ERROR")
            return False
        
        generated = response.get("generated", False)
        is_mock = response.get("mock", False)
        
        if generated:
            # Real image generation
            if "image_base64" not in response or "image_url" not in response:
                self.log("❌ Generated image should have image_base64 and image_url", "ERROR")
                return False
            self.log("✅ Image generation successful (real image generated)")
        elif is_mock:
            # Mock response due to missing API key
            if "message" not in response:
                self.log("❌ Mock response should have message field", "ERROR")
                return False
            self.log("✅ Image generation returned mock response (API key not configured)")
        else:
            self.log("❌ Image generation failed without mock fallback", "ERROR")
            return False
        
        # Check that style was preserved
        if response.get("style") != "minimal":
            self.log(f"❌ Style should be 'minimal', got {response.get('style')}", "ERROR")
            return False
        
        return True
    
    async def test_voice_narration(self):
        """Test POST /api/content/narrate."""
        self.log("=== Testing Voice Narration ===")
        
        # Try to use an existing completed job first
        existing_job_id = None
        if self.job_ids:
            for job_id in self.job_ids:
                status, response = self.test_api_call("GET", f"/content/job/{job_id}")
                if status == 200 and response.get("status") == "reviewing":
                    existing_job_id = job_id
                    self.log(f"Using existing completed job: {job_id}")
                    break
        
        if not existing_job_id:
            # Create a job with content to narrate
            content_data = {
                "platform": "linkedin",
                "content_type": "post", 
                "raw_input": "Explore blockchain technology in financial systems."
            }
            
            status, response = self.test_api_call("POST", "/content/create", content_data)
            
            if status != 200 or "job_id" not in response:
                self.log("❌ Failed to create job for voice narration test", "ERROR")
                return False
            
            existing_job_id = response["job_id"]
            self.job_ids.append(existing_job_id)
            
            # Wait for job to complete with shorter timeout
            if not await self.poll_job_until_ready(existing_job_id, max_wait=30):
                self.log("❌ Job failed to complete quickly, testing with partial job", "ERROR")
                # Continue with test anyway
        
        # Test voice narration
        voice_data = {
            "job_id": existing_job_id,
            "stability": 0.6,
            "similarity_boost": 0.8
        }
        
        status, response = self.test_api_call("POST", "/content/narrate", voice_data)
        
        if status != 200:
            self.log(f"❌ Voice narration failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Voice response should be a dict", "ERROR")
            return False
        
        # Check response structure - both real and mock responses are acceptable
        expected_fields = ["generated", "voice_used", "duration_estimate"]
        missing_fields = [field for field in expected_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in voice response: {missing_fields}", "ERROR")
            return False
        
        generated = response.get("generated", False) 
        is_mock = response.get("mock", False)
        
        if generated:
            # Real voice generation
            if "audio_base64" not in response or "audio_url" not in response:
                self.log("❌ Generated audio should have audio_base64 and audio_url", "ERROR")
                return False
            self.log("✅ Voice narration successful (real audio generated)")
        elif is_mock:
            # Mock response due to missing API key
            if "message" not in response:
                self.log("❌ Mock response should have message field", "ERROR") 
                return False
            self.log("✅ Voice narration returned mock response (ELEVENLABS_API_KEY placeholder)")
        else:
            self.log("❌ Voice narration failed without mock fallback", "ERROR")
            return False
        
        # Check duration estimate
        duration = response.get("duration_estimate", 0)
        if not isinstance(duration, (int, float)) or duration <= 0:
            self.log("❌ Duration estimate should be a positive number", "ERROR")
            return False
        
        # Check voice info
        voice_used = response.get("voice_used", {})
        if not isinstance(voice_used, dict) or "name" not in voice_used:
            self.log("❌ voice_used should be a dict with name field", "ERROR") 
            return False
        
        self.log(f"Voice used: {voice_used.get('name')}, Duration: {duration}s")
        return True
    
    async def test_daily_brief_api_initial(self):
        """Test Daily Brief API endpoint (first call, should generate new brief)."""
        self.log("=== Testing Daily Brief API (Initial Call) ===")
        
        status, response = self.test_api_call("GET", "/dashboard/daily-brief")
        
        if status == 200:
            required_fields = [
                "greeting", "date_context", "trending_topics", 
                "content_ideas", "optimal_time", "energy_check", "cached"
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log(f"❌ Missing fields in daily brief: {missing_fields}", "ERROR")
                return False
            
            # Check data structure
            if not isinstance(response.get("trending_topics"), list):
                self.log("❌ trending_topics should be a list", "ERROR")
                return False
            
            if not isinstance(response.get("content_ideas"), list):
                self.log("❌ content_ideas should be a list", "ERROR")
                return False
            
            if not isinstance(response.get("energy_check"), dict):
                self.log("❌ energy_check should be a dict", "ERROR")
                return False
            
            # Should not be cached on first call
            if response.get("cached") != False:
                self.log("❌ First call should not be cached", "ERROR")
                return False
            
            self.log("✅ Daily Brief API working - initial call successful")
            self.log(f"Greeting: {response.get('greeting')}")
            self.log(f"Trending topics count: {len(response.get('trending_topics', []))}")
            self.log(f"Content ideas count: {len(response.get('content_ideas', []))}")
            return True
        else:
            self.log(f"❌ Daily Brief API failed: {response}", "ERROR")
            return False

    async def test_daily_brief_caching(self):
        """Test Daily Brief API caching (second call should return cached=true)."""
        self.log("=== Testing Daily Brief API Caching ===")
        
        status, response = self.test_api_call("GET", "/dashboard/daily-brief")
        
        if status == 200:
            # Second call should be cached
            if response.get("cached") != True:
                self.log("❌ Second call should be cached", "ERROR")
                return False
            
            self.log("✅ Daily Brief caching working correctly")
            return True
        else:
            self.log(f"❌ Daily Brief caching test failed: {response}", "ERROR")
            return False

    async def test_daily_brief_refresh(self):
        """Test Daily Brief API refresh parameter."""
        self.log("=== Testing Daily Brief API Refresh ===")
        
        status, response = self.test_api_call("GET", "/dashboard/daily-brief?refresh=true")
        
        if status == 200:
            # With refresh=true, should not be cached
            if response.get("cached") != False:
                self.log("❌ Refresh call should not be cached", "ERROR")
                return False
            
            self.log("✅ Daily Brief refresh working correctly")
            return True
        else:
            self.log(f"❌ Daily Brief refresh test failed: {response}", "ERROR")
            return False

    async def test_daily_brief_dismiss(self):
        """Test Daily Brief dismiss functionality."""
        self.log("=== Testing Daily Brief Dismiss ===")
        
        # First dismiss the brief
        status, response = self.test_api_call("POST", "/dashboard/daily-brief/dismiss")
        
        if status == 200:
            if "dismissed" not in str(response).lower():
                self.log(f"❌ Unexpected dismiss response: {response}", "ERROR")
                return False
            
            self.log("✅ Daily Brief dismiss successful")
            return True
        else:
            self.log(f"❌ Daily Brief dismiss failed: {response}", "ERROR")
            return False

    async def test_daily_brief_status(self):
        """Test Daily Brief status endpoint after dismissal."""
        self.log("=== Testing Daily Brief Status ===")
        
        status, response = self.test_api_call("GET", "/dashboard/daily-brief/status")
        
        if status == 200:
            required_fields = ["show_brief", "dismissed_today"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log(f"❌ Missing fields in brief status: {missing_fields}", "ERROR")
                return False
            
            # After dismissal, should return show_brief=false
            if response.get("show_brief") != False:
                self.log("❌ show_brief should be false after dismissal", "ERROR")
                return False
            
            if response.get("dismissed_today") != True:
                self.log("❌ dismissed_today should be true after dismissal", "ERROR")
                return False
            
            self.log("✅ Daily Brief status working correctly")
            return True
        else:
            self.log(f"❌ Daily Brief status test failed: {response}", "ERROR")
            return False

    async def test_dashboard_stats_sprint4_compatibility(self):
        """Test that Sprint 4 dashboard stats still work."""
        self.log("=== Testing Sprint 4 Dashboard Stats Compatibility ===")
        
        status, response = self.test_api_call("GET", "/dashboard/stats")
        
        if status == 200:
            required_fields = [
                "posts_created", "credits", "platforms_count", 
                "persona_score", "learning_signals_count", "recent_jobs"
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log(f"❌ Missing fields in dashboard stats: {missing_fields}", "ERROR")
                return False
            
            self.log("✅ Sprint 4 Dashboard Stats compatibility maintained")
            return True
        else:
            self.log(f"❌ Dashboard stats compatibility test failed: {response}", "ERROR")
            return False
    
    async def test_content_creation(self):
        """Test content creation flow."""
        self.log("=== Testing Content Creation Flow ===")
        
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "AI is transforming the workplace by automating routine tasks and freeing humans to focus on creative problem-solving."
        }
        
        status, response = self.test_api_call("POST", "/content/create", content_data)
        
        if status == 200:
            if isinstance(response, dict) and "job_id" in response:
                job_id = response["job_id"]
                self.job_ids.append(job_id)
                self.log(f"✅ Content creation started: {job_id}")
                return job_id
            else:
                self.log("❌ Content creation response missing job_id", "ERROR")
                return None
        else:
            self.log(f"❌ Content creation failed: {response}", "ERROR")
            return None
    
    async def poll_job_until_ready(self, job_id, max_wait=60):
        """Poll job until it's ready for review."""
        self.log(f"=== Polling job {job_id} until ready ===")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status, response = self.test_api_call("GET", f"/content/job/{job_id}")
            
            if status == 200:
                job_status = response.get("status", "unknown")
                current_agent = response.get("current_agent", "unknown")
                
                self.log(f"Job status: {job_status}, agent: {current_agent}")
                
                if job_status == "reviewing":
                    self.log("✅ Job ready for review")
                    return True
                elif job_status == "error":
                    self.log(f"❌ Job failed with error: {response.get('error', 'Unknown error')}", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to poll job: {response}", "ERROR")
                return False
            
            await asyncio.sleep(3)
        
        self.log("❌ Job polling timed out", "ERROR")
        return False
    
    async def test_content_approval(self, job_id):
        """Test content approval and learning signal capture."""
        self.log(f"=== Testing Content Approval for {job_id} ===")
        
        approval_data = {
            "status": "approved"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status == 200:
            if "approved" in str(response).lower():
                self.log("✅ Content approval successful")
                return True
            else:
                self.log(f"❌ Unexpected approval response: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Content approval failed: {response}", "ERROR")
            return False
    
    async def test_idempotency_check(self, job_id):
        """Test that approving an already approved job returns appropriate message."""
        self.log(f"=== Testing Idempotency for {job_id} ===")
        
        approval_data = {
            "status": "approved"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status == 200:
            if "already" in str(response).lower():
                self.log("✅ Idempotency check working")
                return True
            else:
                self.log(f"❌ Idempotency not working properly: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Idempotency test failed: {response}", "ERROR")
            return False
    
    async def test_dashboard_stats_updated(self):
        """Test dashboard stats after content approval."""
        self.log("=== Testing Dashboard Stats (After Approval) ===")
        
        # Wait a bit for background task to complete
        await asyncio.sleep(3)
        
        status, response = self.test_api_call("GET", "/dashboard/stats")
        
        if status == 200:
            posts_created = response.get("posts_created", 0)
            learning_signals = response.get("learning_signals_count", 0)
            recent_jobs = response.get("recent_jobs", [])
            
            if posts_created < 1:
                self.log(f"❌ posts_created should be at least 1 after approval, got {posts_created}", "ERROR")
                return False
            
            if learning_signals < 1:
                self.log(f"❌ learning_signals_count should be at least 1 after approval, got {learning_signals}", "ERROR")
                return False
            
            if len(recent_jobs) < 1:
                self.log(f"❌ recent_jobs should show at least 1 job, got {len(recent_jobs)}", "ERROR")
                return False
            
            # Check that recent job shows approved status
            recent_job = recent_jobs[0]
            if recent_job.get("status") != "approved":
                self.log(f"❌ Recent job should show approved status, got {recent_job.get('status')}", "ERROR")
                return False
            
            self.log("✅ Dashboard stats updated correctly after approval")
            return True
        else:
            self.log(f"❌ Dashboard stats API failed: {response}", "ERROR")
            return False
    
    async def test_second_content_creation(self):
        """Create second content to test anti-repetition."""
        self.log("=== Testing Second Content Creation (Anti-Repetition) ===")
        
        # Similar but different content to test anti-repetition
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Artificial intelligence is revolutionizing business operations by streamlining processes and enhancing human productivity."
        }
        
        job_id = await self.test_content_creation()
        if not job_id:
            return None
        
        # Poll until ready
        if not await self.poll_job_until_ready(job_id):
            return None
        
        # Check if QC output includes repetition fields
        status, response = self.test_api_call("GET", f"/content/job/{job_id}")
        
        if status == 200:
            qc_output = response.get("qc_score", {})
            
            # Check for repetition risk fields
            if "repetition_risk" not in qc_output:
                self.log("❌ QC output missing repetition_risk field", "ERROR")
                return None
            
            if "repetition_level" not in qc_output:
                self.log("❌ QC output missing repetition_level field", "ERROR")
                return None
            
            rep_risk = qc_output.get("repetition_risk", 0)
            rep_level = qc_output.get("repetition_level", "none")
            
            self.log(f"✅ Anti-repetition working: risk={rep_risk}, level={rep_level}")
            
            # Since this is similar content, we expect some repetition risk
            if rep_risk > 50 or rep_level in ["medium", "high"]:
                self.log("✅ Anti-repetition engine detected similarity as expected")
            else:
                self.log("ℹ️ Anti-repetition showed low risk (may be expected with mock mode)")
            
            return job_id
        else:
            self.log(f"❌ Failed to check second job: {response}", "ERROR")
            return None
    
    async def test_content_rejection(self):
        """Test content rejection flow."""
        self.log("=== Testing Content Rejection Flow ===")
        
        # Create third content for rejection test
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Testing rejection flow for learning signal capture"
        }
        
        job_id = await self.test_content_creation()
        if not job_id:
            return False
        
        # Poll until ready
        if not await self.poll_job_until_ready(job_id):
            return False
        
        # Reject the content
        rejection_data = {
            "status": "rejected",
            "rejection_reason": "Testing rejection flow"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", rejection_data)
        
        if status == 200:
            if "rejected" in str(response).lower():
                self.log("✅ Content rejection successful")
                return True
            else:
                self.log(f"❌ Unexpected rejection response: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Content rejection failed: {response}", "ERROR")
            return False

    async def run_all_tests(self):
        """Run all backend tests in sequence."""
        print(f"\n🚀 Starting ThookAI Sprint 6 Backend Tests")
        print(f"Backend URL: {API_BASE}")
        print("=" * 60)
        
        test_results = {}
        
        # Authentication
        test_results["auth"] = await self.test_auth_flow()
        if not test_results["auth"]:
            print("❌ Authentication failed - stopping tests")
            return test_results
        
        # SPRINT 6 PRIORITY TESTS
        
        # Quick endpoint tests
        test_results["image_styles"] = await self.test_image_styles_endpoint()
        test_results["voices_list"] = await self.test_voices_endpoint()
        
        # Content regeneration flow (HIGH PRIORITY)
        regen_result = await self.test_content_regeneration_flow()
        test_results["content_regeneration"] = regen_result is not None
        
        # Job history test (depends on regeneration)
        if regen_result:
            test_results["job_history"] = await self.test_job_history_endpoint(regen_result)
        else:
            test_results["job_history"] = False
            self.log("❌ Skipping job history test due to regeneration failure", "ERROR")
        
        # Image generation (with 90s timeout)
        test_results["image_generation"] = await self.test_image_generation()
        
        # Voice narration
        test_results["voice_narration"] = await self.test_voice_narration()
        
        # Optional: Sprint 5 compatibility tests
        test_results["daily_brief_initial"] = await self.test_daily_brief_api_initial()
        test_results["dashboard_stats_compatibility"] = await self.test_dashboard_stats_sprint4_compatibility()
        
        return test_results

async def main():
    """Main test runner."""
    runner = TestRunner()
    results = await runner.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🏁 SPRINT 6 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    for test_name, result in results.items():
        total += 1
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)