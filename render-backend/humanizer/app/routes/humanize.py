from fastapi import APIRouter, HTTPException

from app.core.humanizer import humanize, rewrite_sentence
from app.providers import AVAILABLE, ProviderError
from app.schemas import (
    HumanizeRequest,
    HumanizeResponse,
    SentenceRequest,
    SentenceResponse,
)

router = APIRouter(tags=["humanize"])


@router.post("/humanize", response_model=HumanizeResponse)
async def humanize_route(req: HumanizeRequest):
    try:
        result = await humanize(
            text=req.text,
            tone=req.tone,
            reading_level=req.reading_level,
            strength=req.strength,
            keep_length=req.keep_length,
            provider_name=req.provider,
            profile_id=req.profile_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return result


@router.post("/rewrite-sentence", response_model=SentenceResponse)
async def rewrite_sentence_route(req: SentenceRequest):
    """Ek jumla dobara likhne ke liye — 'regenerate this line' button."""
    try:
        out = await rewrite_sentence(
            sentence=req.sentence,
            profile_id=req.profile_id,
            tone=req.tone,
            provider_name=req.provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"output": out}


@router.get("/providers")
async def list_providers():
    return {"available": AVAILABLE}
