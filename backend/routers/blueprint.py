from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.blueprint_service import generate_blueprint, BlueprintProposal

router = APIRouter(prefix="/api/v1/blueprint", tags=["Blueprint"])

class BlueprintRequest(BaseModel):
    description: str

@router.post("/generate", response_model=BlueprintProposal)
async def create_blueprint_proposal(req: BlueprintRequest):
    return await generate_blueprint(req.description)
