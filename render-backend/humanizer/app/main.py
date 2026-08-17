"""
FastAPI app — ToolNest unified local server
Ek hi server pe: Home + PDF + Humanizer + Clipper(soon).
Chalane ke liye:  python run.py   ->  http://localhost:8000
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx

from app.config import settings
from app.routes import analyze, humanize, profiles

STATIC_DIR = Path(__file__).parent / "static"
# ToolNest/  (humanizer/app/main.py -> up 3 = ToolNest)
ROOT_DIR = Path(__file__).parent.parent.parent
PDF_INDEX = ROOT_DIR / "pdf" / "index.html"

app = FastAPI(
    title="ToolNest",
    description="Free tools: PDF, AI Humanizer, Video Clipper.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(humanize.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
next_static_dir = ROOT_DIR / "clipper" / "frontend" / "out" / "_next"
if next_static_dir.exists():
    app.mount("/_next", StaticFiles(directory=next_static_dir), name="next_static")

@app.get("/health")
async def health():
    return {"status": "ok", "provider": settings.llm_provider}

# ---------- Clipper API Proxy ----------
# Catch-all for Clipper API requests going to port 8000 instead of 5000
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def clipper_api_proxy(request: Request, path: str):
    clipper_routes = ["upload", "youtube", "jobs", "download", "preview"]
    if any(path.startswith(route) for route in clipper_routes):
        target_url = f"http://localhost:5000/api/{path}"
        
        headers = dict(request.headers)
        headers.pop("host", None) # Remove host header so httpx sets the correct one
        
        # Read body
        body = await request.body()
        
        # Use a global or unmanaged client, or just read the full response for now
        # since it's local to local. For download routes, we might need streaming.
        client = httpx.AsyncClient()
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        from fastapi.responses import Response
        res = Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        await client.aclose()
        return res
    
    # If not a clipper route, return 404 natively (though it should be caught by earlier routers if it existed)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Not Found")


# ---------- ToolNest pages (one site) ----------

# Home = ToolNest landing
@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "home.html")


# PDF suite (29+ tools)
@app.get("/pdf")
async def pdf_tool():
    if PDF_INDEX.exists():
        return FileResponse(PDF_INDEX)
    return FileResponse(STATIC_DIR / "home.html")


# AI Humanizer tool
@app.get("/humanizer")
async def humanizer_tool():
    return FileResponse(STATIC_DIR / "index.html")


# Video Clipper
@app.get("/clipper")
@app.get("/clipper/{full_path:path}")
async def clipper_tool(full_path: str = ""):
    out_index = ROOT_DIR / "clipper" / "frontend" / "out" / "index.html"
    if out_index.exists():
        return FileResponse(out_index)
    return FileResponse(STATIC_DIR / "clipper-soon.html")


# ---------- Humanizer sub-pages ----------

@app.get("/use-cases/{page}")
async def use_case_page(page: str):
    f = STATIC_DIR / "use-cases" / f"{page}.html"
    if f.exists():
        return FileResponse(f)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/blog")
@app.get("/blog/")
async def blog_index():
    return FileResponse(STATIC_DIR / "blog" / "index.html")


@app.get("/blog/{slug}")
async def blog_post(slug: str):
    f = STATIC_DIR / "blog" / f"{slug}.html"
    if f.exists():
        return FileResponse(f)
    return FileResponse(STATIC_DIR / "blog" / "index.html")


# ---------- SEO ----------

@app.get("/sitemap.xml")
async def sitemap():
    return FileResponse(STATIC_DIR / "sitemap.xml", media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    return FileResponse(STATIC_DIR / "robots.txt", media_type="text/plain")
