from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ResourceCreate, ResourceUpdate, ResourceResponse, ResourceListResponse
from app.services import ResourceService
from app.models import ResourceType, ResourceStatus
from typing import Optional

router = APIRouter(prefix="/resources", tags=["资源管理"])


@router.post("", response_model=ResourceResponse, summary="创建资源")
def create_resource(resource_data: ResourceCreate, db: Session = Depends(get_db)):
    resource = ResourceService.create_resource(db, resource_data)
    return resource


@router.get("", response_model=ResourceListResponse, summary="资源列表")
def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[ResourceType] = None,
    status: Optional[ResourceStatus] = None,
    floor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    items, total = ResourceService.list_resources(db, page, page_size, type, status, floor)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{resource_id}", response_model=ResourceResponse, summary="资源详情")
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = ResourceService.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    return resource


@router.put("/{resource_id}", response_model=ResourceResponse, summary="更新资源")
def update_resource(
    resource_id: int,
    update_data: ResourceUpdate,
    db: Session = Depends(get_db)
):
    updated = ResourceService.update_resource(db, resource_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="资源不存在")
    return updated


@router.delete("/{resource_id}", summary="删除资源")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    success = ResourceService.delete_resource(db, resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="资源不存在")
    return {"message": "删除成功"}


@router.get("/{resource_id}/availability", summary="检查资源可用性")
def check_availability(
    resource_id: int,
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db)
):
    from datetime import datetime
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="时间格式错误，请使用ISO格式")

    available = ResourceService.is_resource_available(db, resource_id, start, end)
    return {"available": available, "resource_id": resource_id}
