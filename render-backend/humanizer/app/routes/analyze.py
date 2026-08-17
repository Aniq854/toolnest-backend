from fastapi import APIRouter

from app.core import readability
from app.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_route(req: AnalyzeRequest):
    """
    Sirf metrics — koi LLM call nahi, is liye bilkul free aur foran.
    """
    m = readability.analyze(req.text)
    return {"metrics": m, "suggestions": readability.suggestions(m)}
