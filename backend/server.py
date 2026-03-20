from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from routes.auth import router as auth_router
from routes.onboarding import router as onboarding_router
from routes.persona import router as persona_router
from routes.content import router as content_router
from routes.dashboard import router as dashboard_router
from routes.platforms import router as platforms_router
from routes.repurpose import router as repurpose_router
from routes.analytics import router as analytics_router
from routes.billing import router as billing_router
from routes.viral import router as viral_router
from routes.agency import router as agency_router
from routes.templates import router as templates_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="ThookAI API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(onboarding_router)
api_router.include_router(persona_router)
api_router.include_router(content_router)
api_router.include_router(dashboard_router)
api_router.include_router(platforms_router)
api_router.include_router(repurpose_router)
api_router.include_router(analytics_router)
api_router.include_router(billing_router)
api_router.include_router(viral_router)
api_router.include_router(agency_router)
api_router.include_router(templates_router)


@api_router.get("/")
async def root():
    return {"message": "ThookAI API v1.0", "status": "running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    from database import client
    client.close()
