from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_actor_landlord_id, get_current_user
from app.file_storage import save_upload_file
from app.models import Upload, User
from app.schemas import UploadRead

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadRead)
def upload_file(
    purpose: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    path = save_upload_file(file, purpose)

    upload = Upload(
        landlord_id=get_actor_landlord_id(db, user),
        owner_user_id=user.id,
        file_path=path,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        purpose=purpose,
    )

    db.add(upload)
    db.commit()
    db.refresh(upload)

    return upload
