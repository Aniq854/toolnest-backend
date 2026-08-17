from fastapi import APIRouter, HTTPException

from app.core import style_profile
from app.providers import ProviderError
from app.schemas import ProfileCreateRequest, ProfileDetail, ProfileSummary

router = APIRouter(tags=["profiles"])


@router.get("/profiles", response_model=list[ProfileSummary])
async def list_route():
    return style_profile.list_profiles()


@router.post("/profiles", response_model=ProfileDetail, status_code=201)
async def create_route(req: ProfileCreateRequest):
    try:
        profile = await style_profile.build_profile(
            name=req.name, samples=req.samples, provider_name=req.provider
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return style_profile.save_profile(profile)


@router.get("/profiles/{profile_id}", response_model=ProfileDetail)
async def get_route(profile_id: str):
    profile = style_profile.load_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile nahi mila.")
    return profile


@router.delete("/profiles/{profile_id}")
async def delete_route(profile_id: str):
    if not style_profile.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile nahi mila.")
    return {"deleted": profile_id}
