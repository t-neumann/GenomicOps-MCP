# src/server/api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .tools import liftover_coordinates, get_annotations

router = APIRouter()

class LiftoverRequest(BaseModel):
    chrom: str
    start: int
    end: int
    from_assembly: str
    to_assembly: str

class AnnotationRequest(BaseModel):
    chrom: str
    start: int
    end: int
    genome: str

@router.post("/liftover")
def liftover(req: LiftoverRequest):
    try:
        result = liftover_coordinates(req.chrom, req.start, req.end, req.from_assembly, req.to_assembly)
        return {"liftover": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/annotations")
def annotations(req: AnnotationRequest):
    try:
        result = get_annotations(req.chrom, req.start, req.end, req.genome)
        return {"annotations": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))