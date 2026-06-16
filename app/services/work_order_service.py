from sqlalchemy.orm import Session
from app.models import WorkOrder, Engineer, Equipment, WorkOrderStatus, EquipmentStatus, FaultType, FaultSeverity, MaintenanceRecord
from app.schemas import EngineerCreate, MaintenanceRecordCreate
from app.services.notification_service import notify_work_order_created, notify_work_order_escalated, notify_work_order_assigned
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import random


class WorkOrderService:
    @staticmethod
    def create_from_anomaly(
        db: Session,
        equipment: Equipment,
        fault_types: List[FaultType],
        severity: FaultSeverity
    ) -> WorkOrder:
        main_fault_type = fault_types[0] if fault_types else FaultType.OTHER

        description_parts = []
        for ft in fault_types:
            if ft == FaultType.OVERHEAT:
                description_parts.append("温度过热告警")
            elif ft == FaultType.OVERCURRENT:
                description_parts.append("电流过载告警")
            elif ft == FaultType.OFFLINE:
                description_parts.append("设备离线告警")
            else:
                description_parts.append(ft.value)
        description = "、".join(description_parts) if description_parts else "设备异常告警"

        work_order = WorkOrder(
            equipment_id=equipment.id,
            fault_type=main_fault_type,
            severity=severity,
            status=WorkOrderStatus.PENDING,
            description=description,
            floor=equipment.floor,
            area=equipment.area,
            location=equipment.location,
            escalation_level=0
        )
        db.add(work_order)
        db.flush()

        engineer = WorkOrderService._select_engineer(db, equipment, fault_types)
        if engineer:
            work_order.engineer_id = engineer.id
            work_order.status = WorkOrderStatus.ASSIGNED
            work_order.assigned_at = datetime.now()

        db.commit()
        db.refresh(work_order)

        if engineer:
            notify_work_order_assigned(db, work_order, engineer)

        return work_order

    @staticmethod
    def _select_engineer(
        db: Session,
        equipment: Equipment,
        fault_types: List[FaultType]
    ) -> Optional[Engineer]:
        all_available = db.query(Engineer).filter(Engineer.is_available == True).all()
        if not all_available:
            return None

        fault_type_strs = [ft.value for ft in fault_types]
        equipment_type_str = equipment.type.value if equipment.type else ""

        floor_matched = []
        specialty_floor_matched = []
        specialty_matched = []

        for eng in all_available:
            floor_match = False
            if eng.floor_range:
                try:
                    if "-" in eng.floor_range:
                        start, end = eng.floor_range.split("-")
                        if int(start) <= equipment.floor <= int(end):
                            floor_match = True
                    else:
                        floors = [int(x.strip()) for x in eng.floor_range.split(",")]
                        if equipment.floor in floors:
                            floor_match = True
                except (ValueError, AttributeError):
                    floor_match = False
            else:
                floor_match = True

            specialty_match = False
            if eng.specialty:
                specialty_lower = eng.specialty.lower()
                for ft_str in fault_type_strs:
                    if ft_str in specialty_lower:
                        specialty_match = True
                        break
                if equipment_type_str and equipment_type_str in specialty_lower:
                    specialty_match = True
            else:
                specialty_match = True

            if floor_match and specialty_match:
                specialty_floor_matched.append(eng)
            elif floor_match:
                floor_matched.append(eng)
            elif specialty_match:
                specialty_matched.append(eng)

        if specialty_floor_matched:
            return random.choice(specialty_floor_matched)
        elif floor_matched:
            return random.choice(floor_matched)
        elif specialty_matched:
            return random.choice(specialty_matched)
        else:
            return all_available[0]

    @staticmethod
    def assign_engineer(
        db: Session,
        order_id: int,
        engineer_id: int
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        work_order = WorkOrderService.get_order_by_id(db, order_id)
        if not work_order:
            return False, "工单不存在", None

        engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
        if not engineer:
            return False, "工程师不存在", None

        work_order.engineer_id = engineer_id
        work_order.status = WorkOrderStatus.ASSIGNED
        work_order.assigned_at = datetime.now()
        db.commit()
        db.refresh(work_order)

        notify_work_order_assigned(db, work_order, engineer)

        return True, "分配成功", work_order

    @staticmethod
    def accept_order(
        db: Session,
        order_id: int,
        engineer_id: int
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        work_order = WorkOrderService.get_order_by_id(db, order_id)
        if not work_order:
            return False, "工单不存在", None

        if work_order.engineer_id != engineer_id:
            return False, "只有被分配的工程师才能接单", None

        if work_order.status not in [WorkOrderStatus.PENDING, WorkOrderStatus.ASSIGNED, WorkOrderStatus.ESCALATED]:
            return False, f"当前状态{work_order.status.value}无法接单", None

        work_order.status = WorkOrderStatus.ACCEPTED
        work_order.accepted_at = datetime.now()
        db.commit()
        db.refresh(work_order)

        return True, "接单成功", work_order

    @staticmethod
    def start_process(
        db: Session,
        order_id: int,
        engineer_id: int,
        remark: str = ""
    ) -> Tuple[bool, str]:
        work_order = WorkOrderService.get_order_by_id(db, order_id)
        if not work_order:
            return False, "工单不存在"

        if work_order.engineer_id != engineer_id:
            return False, "只有被分配的工程师才能开始处理"

        if work_order.status not in [WorkOrderStatus.ACCEPTED]:
            return False, f"当前状态{work_order.status.value}无法开始处理"

        work_order.status = WorkOrderStatus.IN_PROGRESS
        if remark:
            work_order.remark = remark
        db.commit()

        return True, "开始处理成功"

    @staticmethod
    def complete_order(
        db: Session,
        order_id: int,
        engineer_id: int,
        remark: str = ""
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        work_order = WorkOrderService.get_order_by_id(db, order_id)
        if not work_order:
            return False, "工单不存在", None

        if work_order.engineer_id != engineer_id:
            return False, "只有被分配的工程师才能完成工单", None

        if work_order.status not in [WorkOrderStatus.IN_PROGRESS]:
            return False, f"当前状态{work_order.status.value}无法完成", None

        work_order.status = WorkOrderStatus.COMPLETED
        work_order.completed_at = datetime.now()
        if remark:
            work_order.remark = remark

        equipment = work_order.equipment
        if equipment:
            equipment.status = EquipmentStatus.ONLINE

        db.commit()
        db.refresh(work_order)

        return True, "工单完成成功", work_order

    @staticmethod
    def get_order_by_id(db: Session, order_id: int) -> Optional[WorkOrder]:
        return db.query(WorkOrder).filter(WorkOrder.id == order_id).first()

    @staticmethod
    def list_orders(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[WorkOrderStatus] = None,
        floor: Optional[int] = None,
        fault_type: Optional[FaultType] = None,
        engineer_id: Optional[int] = None
    ) -> Tuple[List[WorkOrder], int]:
        query = db.query(WorkOrder)
        if status:
            query = query.filter(WorkOrder.status == status)
        if floor is not None:
            query = query.filter(WorkOrder.floor == floor)
        if fault_type:
            query = query.filter(WorkOrder.fault_type == fault_type)
        if engineer_id is not None:
            query = query.filter(WorkOrder.engineer_id == engineer_id)
        total = query.count()
        items = query.order_by(WorkOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def list_engineers(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        is_available: Optional[bool] = None
    ) -> Tuple[List[Engineer], int]:
        query = db.query(Engineer)
        if is_available is not None:
            query = query.filter(Engineer.is_available == is_available)
        total = query.count()
        items = query.order_by(Engineer.id).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def create_engineer(db: Session, engineer_data: EngineerCreate) -> Engineer:
        db_engineer = Engineer(**engineer_data.model_dump())
        db.add(db_engineer)
        db.commit()
        db.refresh(db_engineer)
        return db_engineer

    @staticmethod
    def check_timeout_and_escalate(db: Session) -> int:
        timeout_threshold = timedelta(minutes=30)
        now = datetime.now()
        count = 0

        pending_orders = db.query(WorkOrder).filter(
            WorkOrder.status == WorkOrderStatus.PENDING
        ).all()

        for order in pending_orders:
            if order.created_at and (now - order.created_at) > timeout_threshold:
                WorkOrderService._escalate_order(db, order, now)
                count += 1

        assigned_orders = db.query(WorkOrder).filter(
            WorkOrder.status == WorkOrderStatus.ASSIGNED
        ).all()

        for order in assigned_orders:
            if order.assigned_at and (now - order.assigned_at) > timeout_threshold:
                WorkOrderService._escalate_order(db, order, now)
                count += 1

        accepted_orders = db.query(WorkOrder).filter(
            WorkOrder.status == WorkOrderStatus.ACCEPTED
        ).all()

        for order in accepted_orders:
            if order.accepted_at and (now - order.accepted_at) > timeout_threshold:
                WorkOrderService._escalate_order(db, order, now)
                count += 1

        db.commit()
        return count

    @staticmethod
    def _escalate_order(db: Session, order: WorkOrder, now: datetime):
        order.escalation_level += 1
        order.status = WorkOrderStatus.ESCALATED
        order.escalated_at = now
        notify_work_order_escalated(db, order, order.escalation_level + 1)

    @staticmethod
    def complete_work_order(
        db: Session,
        work_order_id: int,
        engineer_id: int,
        record_data: MaintenanceRecordCreate
    ) -> Tuple[bool, str, Optional[WorkOrder], Optional[MaintenanceRecord]]:
        work_order = WorkOrderService.get_order_by_id(db, work_order_id)
        if not work_order:
            return False, "工单不存在", None, None

        if work_order.engineer_id != engineer_id:
            return False, "只有被分配的工程师才能完成工单", None, None

        if work_order.status not in [WorkOrderStatus.IN_PROGRESS]:
            return False, f"当前状态{work_order.status.value}无法完成", None, None

        work_order.status = WorkOrderStatus.COMPLETED
        work_order.completed_at = datetime.now()

        now = datetime.now()
        maintenance_record = MaintenanceRecord(
            work_order_id=work_order_id,
            equipment_id=work_order.equipment_id,
            engineer_id=engineer_id,
            result=record_data.result,
            materials_used=record_data.materials_used,
            photo_url=record_data.photo_url,
            needs_recheck=record_data.needs_recheck or False,
            recheck_date=record_data.recheck_date,
            remark=record_data.remark,
            created_at=now,
            updated_at=now
        )
        db.add(maintenance_record)

        equipment = work_order.equipment
        if equipment:
            equipment.status = EquipmentStatus.ONLINE
            equipment.fault_count = (equipment.fault_count or 0) + 1
            if equipment.fault_count >= 3:
                equipment.is_frequent_fault = True

        db.commit()
        db.refresh(work_order)
        db.refresh(maintenance_record)

        return True, "工单完成成功", work_order, maintenance_record

    @staticmethod
    def get_maintenance_records_by_equipment(
        db: Session,
        equipment_id: int
    ) -> List[MaintenanceRecord]:
        return db.query(MaintenanceRecord).filter(
            MaintenanceRecord.equipment_id == equipment_id
        ).order_by(MaintenanceRecord.created_at.desc()).all()

    @staticmethod
    def list_maintenance_records(
        db: Session,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[MaintenanceRecord], int]:
        query = db.query(MaintenanceRecord)
        total = query.count()
        items = query.order_by(MaintenanceRecord.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        return items, total

    @staticmethod
    def mark_equipment_frequent_fault(
        db: Session,
        equipment_id: int,
        is_frequent: bool
    ) -> Tuple[bool, str, Optional[Equipment]]:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            return False, "设备不存在", None

        equipment.is_frequent_fault = is_frequent
        db.commit()
        db.refresh(equipment)

        return True, "操作成功", equipment
