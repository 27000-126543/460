from sqlalchemy.orm import Session
from app.models import Equipment, EquipmentData, FaultType, FaultSeverity, EquipmentStatus
from app.schemas import EquipmentCreate, EquipmentUpdate, EquipmentDataReport
from app.services.notification_service import notify_work_order_created
from datetime import datetime
from typing import Optional, List, Tuple
import json


class EquipmentService:
    @staticmethod
    def create_equipment(db: Session, equipment_data: EquipmentCreate) -> Equipment:
        db_equipment = Equipment(**equipment_data.model_dump())
        db.add(db_equipment)
        db.commit()
        db.refresh(db_equipment)
        return db_equipment

    @staticmethod
    def get_equipment_by_id(db: Session, equipment_id: int) -> Optional[Equipment]:
        return db.query(Equipment).filter(Equipment.id == equipment_id).first()

    @staticmethod
    def list_equipments(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        type: Optional = None,
        status: Optional = None,
        floor: Optional[int] = None
    ) -> Tuple[List[Equipment], int]:
        query = db.query(Equipment)
        if type:
            query = query.filter(Equipment.type == type)
        if status:
            query = query.filter(Equipment.status == status)
        if floor is not None:
            query = query.filter(Equipment.floor == floor)
        total = query.count()
        items = query.order_by(Equipment.floor, Equipment.name).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def update_equipment(db: Session, equipment_id: int, update_data) -> Optional[Equipment]:
        db_equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
        if not db_equipment:
            return None
        update_dict = update_data.model_dump(exclude_unset=True) if hasattr(update_data, 'model_dump') else update_data
        for key, value in update_dict.items():
            setattr(db_equipment, key, value)
        db.commit()
        db.refresh(db_equipment)
        return db_equipment

    @staticmethod
    def delete_equipment(db: Session, equipment_id: int) -> bool:
        db_equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
        if not db_equipment:
            return False
        db.delete(db_equipment)
        db.commit()
        return True

    @staticmethod
    def detect_anomaly(
        db: Session,
        equipment: Equipment,
        temperature: Optional[float],
        current: Optional[float],
        is_online: bool
    ) -> Tuple[bool, List[dict], FaultSeverity]:
        is_anomaly = False
        anomaly_details = []
        max_severity = FaultSeverity.LOW

        if not is_online:
            is_anomaly = True
            detail = {
                "type": FaultType.OFFLINE.value,
                "message": "设备离线"
            }
            anomaly_details.append(detail)
            if FaultSeverity.HIGH.value > max_severity.value:
                max_severity = FaultSeverity.HIGH

        if temperature is not None and temperature > equipment.temp_threshold:
            is_anomaly = True
            detail = {
                "type": FaultType.OVERHEAT.value,
                "message": f"温度过高：{temperature}°C（阈值：{equipment.temp_threshold}°C）"
            }
            anomaly_details.append(detail)
            if temperature > equipment.temp_threshold * 1.2:
                if FaultSeverity.CRITICAL.value > max_severity.value:
                    max_severity = FaultSeverity.CRITICAL
            else:
                if FaultSeverity.MEDIUM.value > max_severity.value:
                    max_severity = FaultSeverity.MEDIUM

        if current is not None and current > equipment.current_threshold:
            is_anomaly = True
            detail = {
                "type": FaultType.OVERCURRENT.value,
                "message": f"电流过高：{current}A（阈值：{equipment.current_threshold}A）"
            }
            anomaly_details.append(detail)
            if current > equipment.current_threshold * 1.2:
                if FaultSeverity.HIGH.value > max_severity.value:
                    max_severity = FaultSeverity.HIGH
            else:
                if FaultSeverity.MEDIUM.value > max_severity.value:
                    max_severity = FaultSeverity.MEDIUM

        return is_anomaly, anomaly_details, max_severity

    @staticmethod
    def report_data(
        db: Session,
        report_data: EquipmentDataReport
    ) -> Tuple[bool, Optional[int], list]:
        from app.services.work_order_service import WorkOrderService

        equipment = EquipmentService.get_equipment_by_id(db, report_data.equipment_id)
        if not equipment:
            return False, None, []

        temperature = report_data.temperature
        current = report_data.current
        is_online = report_data.is_online if report_data.is_online is not None else True

        is_anomaly, anomaly_details, max_severity = EquipmentService.detect_anomaly(
            db, equipment, temperature, current, is_online
        )

        db_data = EquipmentData(
            equipment_id=report_data.equipment_id,
            temperature=temperature,
            current=current,
            is_online=is_online,
            raw_data=report_data.raw_data,
            is_anomaly=is_anomaly,
            anomaly_details=json.dumps(anomaly_details, ensure_ascii=False) if anomaly_details else None
        )
        db.add(db_data)

        first_work_order_id = None
        if is_anomaly:
            equipment.status = EquipmentStatus.MALFUNCTION

            fault_types = []
            for detail in anomaly_details:
                try:
                    fault_types.append(FaultType(detail["type"]))
                except ValueError:
                    pass

            if fault_types:
                for i, fault_type in enumerate(fault_types):
                    work_order = WorkOrderService.create_from_anomaly(
                        db=db,
                        equipment=equipment,
                        fault_types=[fault_type],
                        severity=max_severity
                    )
                    if i == 0:
                        first_work_order_id = work_order.id
                        notify_work_order_created(db, work_order, work_order.engineer)
        else:
            if is_online:
                equipment.status = EquipmentStatus.ONLINE
            else:
                equipment.status = EquipmentStatus.OFFLINE

        db.commit()
        db.refresh(db_data)
        db.refresh(equipment)

        return is_anomaly, first_work_order_id, anomaly_details

    @staticmethod
    def get_latest_data(db: Session, equipment_id: int) -> Optional[EquipmentData]:
        return db.query(EquipmentData).filter(
            EquipmentData.equipment_id == equipment_id
        ).order_by(EquipmentData.reported_at.desc()).first()
