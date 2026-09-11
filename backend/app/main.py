from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as documents_router
from app.core.database import Base, engine
from app.models.document import Document


app = FastAPI(
    title="Document Intelligence API",
    description="AI-powered financial document extraction and validation platform",
    version="1.0.0",
)


# Allow the separately deployed frontend to communicate with the API.
# We can restrict this to the Vercel domain after the frontend is deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "document-intelligence-api",
    }


app.include_router(documents_router)