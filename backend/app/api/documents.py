"""Authenticated document upload, listing, and deletion routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.core.dependencies import check_rate_limit, get_current_user
from backend.app.models.schemas import DocumentListResponse, DocumentResponse
from backend.app.services.documents import (
    DocumentProcessingError,
    delete_document as remove_document,
    list_documents,
    process_document,
)


router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(check_rate_limit)])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    content = file.file.read(settings.max_upload_bytes + 1)
    try:
        return process_document(user["id"], file.filename, content, file.content_type)
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        file.file.close()


@router.get("", response_model=DocumentListResponse)
def get_documents(user: dict = Depends(get_current_user)) -> dict:
    documents = list_documents(user["id"])
    return {"documents": documents, "total": len(documents)}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user: dict = Depends(get_current_user)) -> None:
    if not remove_document(user["id"], document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
