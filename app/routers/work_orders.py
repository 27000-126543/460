from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    WorkOrderResponse, WorkOrderListResponse,
    WorkOrderAssignRequest, EngineerCreate, EngineerResponse,
    MaintenanceRecordCreate, MaintenanceRecordResponse, MaintenanceRecordListResponse
)
from app.services import WorkOrderService
from app.models import WorkOrderStatus, FaultType, FaultSeverity
from typing import Optional

router = APIRouter(prefix="/work-orders", tags=["工单管理"])
engineer_router = APIRouter(prefix="/engineers", tags=["工程师管理"])
maintenance_router = APIRouter(prefix="/maintenance-records", tags=["维修记录"])


def _enrich_order(order):
    order_dict = order.__dict__.copy()
    order_dict["equipment_name"] = order.equipment.name if order.equipment else ""
    order_dict["engineer_name"] = order.engineer.name if order.engineer else ""
    return order_dict


@router.get("", response_model=WorkOrderListResponse, summary="工单列表")
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[WorkOrderStatus] = None,
    floor: Optional[int] = None,
    fault_type: Optional[FaultType] = None,
    engineer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    items, total = WorkOrderService.list_orders(
        db, page, page_size, status=status, floor=floor,
        fault_type=fault_type, engineer_id=engineer_id
    )
    result = [_enrich_order(o) for o in items]
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/{work_order_id}", response_model=WorkOrderResponse, summary="工单详情")
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db)
):
    work_order = WorkOrderService.get_order_by_id(db, work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    return _enrich_order(work_order)


@router.put("/{work_order_id}/assign", response_model=WorkOrderResponse, summary="分配工单给工程师")
def assign_work_order(
    work_order_id: int,
    request: WorkOrderAssignRequest,
    db: Session = Depends(get_db)
):
    success, msg, work_order = WorkOrderService.assign_engineer(db, work_order_id, request.engineer_id)
    if not work_order:
        raise HTTPException(status_code=404, detail=msg)
    return _enrich_order(work_order)


@router.post("/{work_order_id}/accept", summary="工程师接单")
def accept_work_order(
    work_order_id: int,
    engineer_id: int = Query(..., description="工程师ID"),
    db: Session = Depends(get_db)
):
    success, msg, work_order = WorkOrderService.accept_order(db, work_order_id, engineer_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "data": _enrich_order(work_order) if work_order else None}


@router.post("/{work_order_id}/start", summary="开始处理工单")
def start_work_order(
    work_order_id: int,
    engineer_id: int = Query(..., description="工程师ID"),
    remark: Optional[str] = Query(None, description="备注"),
    db: Session = Depends(get_db)
):
    success, msg = WorkOrderService.start_process(db, work_order_id, engineer_id, remark or "")
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/{work_order_id}/complete", summary="完成工单（带维修记录）")
def complete_work_order(
    work_order_id: int,
    record_data: MaintenanceRecordCreate,
    engineer_id: int = Query(..., description="工程师ID"),
    db: Session = Depends(get_db)
):
    if record_data.work_order_id is not None and record_data.work_order_id != work_order_id:
        raise HTTPException(status_code=400, detail="请求体中的工单编号与路径不一致")
    if record_data.work_order_id is None:
        record_data.work_order_id = work_order_id
    success, msg, work_order, record = WorkOrderService.complete_work_order(db, work_order_id, engineer_id, record_data)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "success": True,
        "message": msg,
        "data": {
            "work_order": _enrich_order(work_order) if work_order else None,
            "maintenance_record": record
        }
    }


@maintenance_router.get("", response_model=MaintenanceRecordListResponse, summary="维修记录列表")
def list_maintenance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    items, total = WorkOrderService.list_maintenance_records(db, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@engineer_router.get("", summary="工程师列表")
def list_engineers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_available: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    items, total = WorkOrderService.list_engineers(db, page, page_size, is_available)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@engineer_router.post("", response_model=EngineerResponse, summary="创建工程师")
def create_engineer(
    engineer_data: EngineerCreate,
    db: Session = Depends(get_db)
):
    engineer = WorkOrderService.create_engineer(db, engineer_data)
    return engineer
