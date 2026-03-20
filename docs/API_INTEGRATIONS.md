# ThookAI — API Integrations Reference

This document lists all third-party API integrations in ThookAI with their purpose, configuration, and usage.

---

## 📋 Integration Summary

| Category | Total Providers | Required | Optional |
|----------|-----------------|----------|----------|
| **LLM/AI** | 5 | 2 | 3 |
| **Image Generation** | 8 | 0 | 8 |
| **Video Generation** | 7 | 0 | 7 |
| **Voice/Audio** | 8 | 0 | 8 |
| **Social Platforms** | 3 | 0 | 3 |
| **Vector Database** | 1 | 0 | 1 |
| **Total** | **32** | **2** | **30** |

---

## 🤖 LLM/AI Providers

### 1. Emergent LLM (REQUIRED)

| | |
|---|---|
| **Purpose** | Universal key for OpenAI/Anthropic/Google models |
| **Used By** | All AI agents (Commander, Scout, Thinker, Writer, QC) |
| **Env Variable** | `EMERGENT_LLM_KEY` |
| **Get Key** | [Emergent Platform](https://emergentagent.com) → Profile → Universal Key |
| **Models Used** | Claude 4 Sonnet (default) |

**Features enabled:**
- Persona generation during onboarding
- Content writing and editing
- Creative angle development
- Quality control review
- Viral hook prediction

---

### 2. Perplexity AI (REQUIRED)

| | |
|---|---|
| **Purpose** | Real-time web research and trend analysis |
| **Used By** | Scout Agent |
| **Env Variable** | `PERPLEXITY_API_KEY` |
| **Get Key** | [Perplexity Settings](https://www.perplexity.ai/settings/api) |
| **Model** | Sonar (latest) |

**Features enabled:**
- Current event research
- Trend identification
- Data point collection
- Competitor analysis

---

### 3. OpenAI (Optional)

| | |
|---|---|
| **Purpose** | Alternative LLM provider |
| **Env Variable** | `OPENAI_API_KEY` |
| **Get Key** | [OpenAI Platform](https://platform.openai.com/api-keys) |

---

### 4. Anthropic (Optional)

| | |
|---|---|
| **Purpose** | Alternative LLM provider |
| **Env Variable** | `ANTHROPIC_API_KEY` |
| **Get Key** | [Anthropic Console](https://console.anthropic.com/settings/keys) |

---

### 5. Google Gemini (Optional)

| | |
|---|---|
| **Purpose** | Alternative LLM provider |
| **Env Variable** | `GEMINI_API_KEY` |
| **Get Key** | [Google AI Studio](https://makersuite.google.com/app/apikey) |

---

## 🖼️ Image Generation Providers

### 1. OpenAI DALL-E 3

| | |
|---|---|
| **Purpose** | High-quality AI image generation |
| **Env Variable** | `OPENAI_IMAGE_API_KEY` |
| **Get Key** | [OpenAI Platform](https://platform.openai.com/api-keys) |
| **Pricing** | ~$0.04-0.08 per image |

**Best for:** Photorealistic images, creative illustrations

---

### 2. Stability AI (Stable Diffusion)

| | |
|---|---|
| **Purpose** | Stable Diffusion XL, SD3, SDXL Turbo |
| **Env Variable** | `STABILITY_API_KEY` |
| **Get Key** | [Stability Platform](https://platform.stability.ai/account/keys) |
| **Pricing** | ~$0.002-0.03 per image |

**Best for:** Artistic styles, custom aesthetics, budget-conscious

---

### 3. FAL AI

| | |
|---|---|
| **Purpose** | Fast inference (FLUX, SDXL Lightning) |
| **Env Variable** | `FAL_API_KEY` |
| **Get Key** | [FAL Dashboard](https://fal.ai/dashboard/keys) |
| **Pricing** | Pay-per-second compute |

**Best for:** Speed-critical applications, real-time generation

---

### 4. Replicate

| | |
|---|---|
| **Purpose** | Multiple models (SDXL, Kandinsky, etc.) |
| **Env Variable** | `REPLICATE_API_TOKEN` |
| **Get Key** | [Replicate](https://replicate.com/account/api-tokens) |
| **Pricing** | Pay-per-second compute |

**Best for:** Model variety, experimentation

---

### 5. Leonardo AI

| | |
|---|---|
| **Purpose** | Creative/artistic image generation |
| **Env Variable** | `LEONARDO_API_KEY` |
| **Get Key** | [Leonardo Settings](https://app.leonardo.ai/settings) |

**Best for:** Gaming assets, concept art

---

### 6. Ideogram

| | |
|---|---|
| **Purpose** | Text-in-image specialist |
| **Env Variable** | `IDEOGRAM_API_KEY` |
| **Get Key** | [Ideogram API](https://ideogram.ai/api) |

**Best for:** Images with text, logos, typography

---

### 7. Midjourney (via proxy)

| | |
|---|---|
| **Purpose** | Artistic, stylized images |
| **Env Variable** | `MIDJOURNEY_API_KEY` |
| **Note** | Requires third-party API proxy service |

**Best for:** Artistic content, unique aesthetics

---

### 8. Google Imagen

| | |
|---|---|
| **Purpose** | Google's image generation |
| **Env Variable** | `GOOGLE_IMAGEN_API_KEY` |
| **Get Key** | Google Cloud Console → Vertex AI |

**Best for:** Enterprise use, Google ecosystem

---

## 🎬 Video Generation Providers

### 1. Runway ML (Gen-3 Alpha)

| | |
|---|---|
| **Purpose** | Highest quality AI video |
| **Env Variable** | `RUNWAY_API_KEY` |
| **Get Key** | [Runway Settings](https://app.runwayml.com/settings) |
| **Pricing** | ~$0.05 per second of video |

**Best for:** Professional quality, cinematic content

---

### 2. Kling AI

| | |
|---|---|
| **Purpose** | High quality, longer videos |
| **Env Variable** | `KLING_API_KEY` |
| **Get Key** | Kling AI Platform |

**Best for:** Extended video content

---

### 3. Pika Labs

| | |
|---|---|
| **Purpose** | Fast text-to-video |
| **Env Variable** | `PIKA_API_KEY` |
| **Get Key** | [Pika](https://pika.art/) |

**Best for:** Quick video generation, social clips

---

### 4. Luma AI (Dream Machine)

| | |
|---|---|
| **Purpose** | Cinematic video generation |
| **Env Variable** | `LUMA_API_KEY` |
| **Get Key** | [Luma Labs](https://lumalabs.ai/) |

**Best for:** Cinematic quality, 3D-aware generation

---

### 5. HeyGen

| | |
|---|---|
| **Purpose** | AI avatars with lip-sync |
| **Env Variable** | `HEYGEN_API_KEY` |
| **Get Key** | [HeyGen Settings](https://app.heygen.com/settings) |

**Best for:** Talking head videos, presentations

---

### 6. Synthesia

| | |
|---|---|
| **Purpose** | Enterprise AI avatars |
| **Env Variable** | `SYNTHESIA_API_KEY` |
| **Get Key** | [Synthesia](https://www.synthesia.io/) |

**Best for:** Corporate training, enterprise content

---

### 7. D-ID

| | |
|---|---|
| **Purpose** | Talking head generation |
| **Env Variable** | `DID_API_KEY` |
| **Get Key** | [D-ID Studio](https://studio.d-id.com/account-settings) |

**Best for:** Personalized video messages

---

## 🎙️ Voice/Audio Providers

### 1. ElevenLabs (Recommended)

| | |
|---|---|
| **Purpose** | Best quality voice cloning & TTS |
| **Env Variable** | `ELEVENLABS_API_KEY` |
| **Get Key** | [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) |
| **Pricing** | ~$0.30 per 1000 characters |

**Best for:** Voice overs, podcast content, voice cloning

---

### 2. OpenAI TTS

| | |
|---|---|
| **Purpose** | Simple, fast text-to-speech |
| **Env Variable** | `OPENAI_TTS_API_KEY` |
| **Get Key** | [OpenAI Platform](https://platform.openai.com/api-keys) |

**Best for:** Quick voiceovers, simple narration

---

### 3. Play.ht

| | |
|---|---|
| **Purpose** | Ultra-realistic voices |
| **Env Variables** | `PLAYHT_API_KEY`, `PLAYHT_USER_ID` |
| **Get Key** | [Play.ht](https://play.ht/studio/api-access) |

**Best for:** Natural conversational voice

---

### 4. Murf.ai

| | |
|---|---|
| **Purpose** | Studio-quality voiceovers |
| **Env Variable** | `MURF_API_KEY` |
| **Get Key** | [Murf.ai](https://murf.ai/) |

**Best for:** Professional voiceovers, multiple languages

---

### 5. Resemble AI

| | |
|---|---|
| **Purpose** | Voice cloning |
| **Env Variable** | `RESEMBLE_API_KEY` |
| **Get Key** | [Resemble AI](https://app.resemble.ai/) |

**Best for:** Custom voice creation, brand voices

---

### 6. Amazon Polly

| | |
|---|---|
| **Purpose** | AWS text-to-speech |
| **Env Variables** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |
| **Get Key** | AWS Console → IAM |

**Best for:** AWS integration, SSML support

---

### 7. Google Cloud TTS

| | |
|---|---|
| **Purpose** | Google's text-to-speech |
| **Env Variable** | `GOOGLE_TTS_API_KEY` |
| **Get Key** | Google Cloud Console |

**Best for:** WaveNet voices, Google ecosystem

---

## 📱 Social Platform Integrations

### 1. LinkedIn

| | |
|---|---|
| **Purpose** | Content publishing, OAuth |
| **Env Variables** | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` |
| **Get Key** | [LinkedIn Developers](https://www.linkedin.com/developers/apps) |
| **Required Scopes** | `r_liteprofile`, `r_emailaddress`, `w_member_social` |

**Features enabled:**
- Post publishing
- Profile data access
- OAuth authentication

---

### 2. Twitter/X

| | |
|---|---|
| **Purpose** | Tweet publishing, threads |
| **Env Variables** | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` |
| **Get Key** | [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) |
| **Required Access** | OAuth 1.0a with Read and Write |

**Features enabled:**
- Tweet publishing
- Thread creation
- Media uploads

---

### 3. Meta (Instagram/Facebook)

| | |
|---|---|
| **Purpose** | Instagram & Facebook publishing |
| **Env Variables** | `META_APP_ID`, `META_APP_SECRET` |
| **Get Key** | [Meta for Developers](https://developers.facebook.com/apps/) |
| **Required Permissions** | `pages_manage_posts`, `instagram_basic`, `instagram_content_publish` |

**Features enabled:**
- Instagram post publishing
- Facebook page posts
- Media uploads

---

## 🗄️ Vector Database

### Pinecone

| | |
|---|---|
| **Purpose** | Vector storage for persona learning |
| **Env Variables** | `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT` |
| **Get Key** | [Pinecone Console](https://app.pinecone.io/) |

**Features enabled:**
- Persona memory storage
- Content similarity search
- Anti-repetition engine
- Learning loops

---

## 📊 Integration Status Endpoint

Check which integrations are configured:

```http
GET /api/content/providers/summary
Authorization: Bearer <token>
```

Response:
```json
{
  "success": true,
  "summary": {
    "image": {
      "configured": 2,
      "total": 8,
      "providers": ["openai", "stability"]
    },
    "video": {
      "configured": 1,
      "total": 7,
      "providers": ["runway"]
    },
    "voice": {
      "configured": 1,
      "total": 8,
      "providers": ["elevenlabs"]
    }
  }
}
```

---

## 🔧 Configuration Priority

For a minimal working setup, configure in this order:

### Tier 1 — Core (Required)
1. `EMERGENT_LLM_KEY` — All AI features
2. `PERPLEXITY_API_KEY` — Research agent

### Tier 2 — Publishing
3. `LINKEDIN_CLIENT_ID` + `LINKEDIN_CLIENT_SECRET`
4. `TWITTER_API_KEY` + secrets
5. `META_APP_ID` + `META_APP_SECRET`

### Tier 3 — Enhanced Content
6. `ELEVENLABS_API_KEY` — Voice content
7. `OPENAI_IMAGE_API_KEY` or `STABILITY_API_KEY` — Images

### Tier 4 — Advanced
8. `PINECONE_API_KEY` — Persona learning
9. `RUNWAY_API_KEY` — Video content
10. Additional creative providers

---

## 💰 Estimated Costs

| Provider | Unit | Est. Cost |
|----------|------|-----------|
| Claude (via Emergent) | 1M tokens | ~$15 |
| Perplexity | Query | ~$0.005 |
| DALL-E 3 | Image | ~$0.04-0.08 |
| Stability AI | Image | ~$0.002-0.03 |
| ElevenLabs | 1K chars | ~$0.30 |
| Runway | 1 sec video | ~$0.05 |
| Pinecone | 1M vectors/mo | ~$70 |

**Typical monthly cost per active user:** $5-20 depending on usage

---

*Last Updated: July 2025*
