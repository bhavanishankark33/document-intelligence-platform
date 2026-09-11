from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes.documents import router as documents_router
from app.core.database import Base, engine
from app.models.document import Document


app = FastAPI(
    title="Document Intelligence API",
    description="AI-powered financial document extraction and validation platform",
    version="1.0.0",
)


app.mount(
    "/static",
    StaticFiles(directory="../frontend/static"),
    name="static",
)


templates = Jinja2Templates(
    directory="../frontend/templates"
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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request},
    )


@app.get("/document", response_class=HTMLResponse)
def document_result(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="document_result.html",
        context={"request": request},
    )


app.include_router(documents_router)