from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Investigation Reports"])

@router.post("/{spill_id}")
def generate_report_json(spill_id: int, db: Session = Depends(get_db)):
    try:
        data = ReportService.generate_dossier_data(db, spill_id)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{spill_id}")
def get_report_json(spill_id: int, db: Session = Depends(get_db)):
    return generate_report_json(spill_id, db)


@router.get("/{spill_id}/html", response_class=HTMLResponse)
def get_report_html(spill_id: int, db: Session = Depends(get_db)):
    try:
        html_content = ReportService.generate_html_report(db, spill_id)
        return HTMLResponse(content=html_content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
