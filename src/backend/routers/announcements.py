from fastapi import APIRouter, HTTPException, Depends, status, Query
from ..database import announcements_collection, teachers_collection
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field


def get_current_user(teacher_username: Optional[str] = Query(None)):
    if not teacher_username:
        return None
    return teachers_collection.find_one({"_id": teacher_username})
class Announcement(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    message: str
    start_date: Optional[str] = None  # ISO format string or None
    expiration_date: str  # ISO format string
    created_by: str

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    start_date: Optional[str] = None
    expiration_date: str

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    start_date: Optional[str] = None
    expiration_date: Optional[str] = None

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.get("/", response_model=List[Announcement])
def list_announcements():
    today = date.today().isoformat()
    # Only return announcements that are not expired
    docs = announcements_collection.find({
        "$or": [
            {"expiration_date": {"$gte": today}},
            {"expiration_date": None}
        ]
    })

    items: List[Announcement] = []
    for doc in docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        items.append(Announcement(**doc))

    return items

@router.post("/", response_model=Announcement, status_code=status.HTTP_201_CREATED)
def create_announcement(data: AnnouncementCreate, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    doc = data.dict()
    doc["created_by"] = user["username"]

    # Use string IDs (consistent with other collections in this codebase)
    from uuid import uuid4

    doc["_id"] = uuid4().hex
    announcements_collection.insert_one(doc)

    return Announcement(**doc)

@router.put("/{announcement_id}", response_model=Announcement)
def update_announcement(announcement_id: str, data: AnnouncementUpdate, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    from pymongo import ReturnDocument

    result = announcements_collection.find_one_and_update(
        {"_id": announcement_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found")

    result["_id"] = str(result.get("_id"))
    return Announcement(**result)

@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(announcement_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return None
