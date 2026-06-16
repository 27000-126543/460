from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    EquipmentListResponse, EquipmentDataReport, EquipmentDataResponse, AnomalyReportResponse,
    MaintenanceRecordResponse
)
from app.services import EquipmentService, WorkOrderService
from app.models import EquipmentType, EquipmentStatus
from typing import Optional, List

router = APIRouter(prefix="/equipments", tags=["设备管理"])


@router.post("", response_model=EquipmentResponse, summary="创建设备")
def create_equipment(
    equipment_data: EquipmentCreate,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.create_equipment(db, equipment_data)
    return equipment


@router.get("", response_model=EquipmentListResponse, summary="设备列表")
def list_equipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[EquipmentType] = None,
    status: Optional[EquipmentStatus] = None,
    floor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    items, total = EquipmentService.list_equipments(db, page, page_size, type, status, floor)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{equipment_id}", response_model=EquipmentResponse, summary="设备详情")
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment


@router.put("/{equipment_id}", response_model=EquipmentResponse, summary="更新设备")
def update_equipment(
    equipment_id: int,
    update_data: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.update_equipment(db, equipment_id, update_data)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment


@router.delete("/{equipment_id}", summary="删除设备")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    success = EquipmentService.delete_equipment(db, equipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"success": True, "message": "删除成功"}


@router.post("/data/report", response_model=AnomalyReportResponse, summary="上报设备数据")
def report_equipment_data(
    data: EquipmentDataReport,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.get_equipment_by_id(db, data.equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")

    is_anomaly, work_order_id, details = EquipmentService.report_data(db, data)
    return AnomalyReportResponse(
        anomaly_detected=is_anomaly,
        work_order_id=work_order_id,
        details=details
    )


@router.get("/{equipment_id}/data/latest", response_model=EquipmentDataResponse, summary="获取最新设备数据")
def get_latest_equipment_data(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")

    latest_data = EquipmentService.get_latest_data(db, equipment_id)
    if not latest_data:
        raise HTTPException(status_code=404, detail="暂无数据")
    return latest_data


@router.get("/{equipment_id}/maintenance-records", response_model=List[MaintenanceRecordResponse], summary="设备历史维修记录")
def get_equipment_maintenance_records(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")

    records = WorkOrderService.get_maintenance_records_by_equipment(db, equipment_id)
    return records


@router.put("/{equipment_id}/frequent-fault", response_model=EquipmentResponse, summary="标记/取消反复故障设备")
def mark_equipment_frequent_fault(
    equipment_id: int,
    is_frequent: bool = Query(..., description="是否标记为反复故障"),
    db: Session = Depends(get_db)
):
    success, msg, equipment = WorkOrderService.mark_equipment_frequent_fault(db, equipment_id, is_frequent)
    if not success:
        raise HTTPException(status_code=404, detail=msg)
    return equipment
