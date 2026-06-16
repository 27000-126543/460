from sqlalchemy.orm import Session
from app.models import Resource, ResourceType, ResourceStatus, Booking, BookingStatus
from app.schemas import ResourceCreate, ResourceUpdate
from datetime import datetime
from typing import Optional, List


class ResourceService:
    @staticmethod
    def create_resource(db: Session, resource_data: ResourceCreate) -> Resource:
        db_resource = Resource(**resource_data.model_dump())
        db.add(db_resource)
        db.commit()
        db.refresh(db_resource)
        return db_resource

    @staticmethod
    def get_resource_by_id(db: Session, resource_id: int) -> Optional[Resource]:
        return db.query(Resource).filter(Resource.id == resource_id).first()

    @staticmethod
    def list_resources(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        type: Optional[ResourceType] = None,
        status: Optional[ResourceStatus] = None,
        floor: Optional[int] = None
    ) -> tuple[List[Resource], int]:
        query = db.query(Resource)
        if type:
            query = query.filter(Resource.type == type)
        if status:
            query = query.filter(Resource.status == status)
        if floor is not None:
            query = query.filter(Resource.floor == floor)
        total = query.count()
        items = query.order_by(Resource.floor, Resource.name).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def update_resource(db: Session, resource_id: int, update_data: ResourceUpdate) -> Optional[Resource]:
        db_resource = ResourceService.get_resource_by_id(db, resource_id)
        if not db_resource:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_resource, key, value)
        db.commit()
        db.refresh(db_resource)
        return db_resource

    @staticmethod
    def delete_resource(db: Session, resource_id: int) -> bool:
        db_resource = ResourceService.get_resource_by_id(db, resource_id)
        if not db_resource:
            return False
        db.delete(db_resource)
        db.commit()
        return True

    @staticmethod
    def is_resource_available(
        db: Session,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> bool:
        resource = ResourceService.get_resource_by_id(db, resource_id)
        if not resource or resource.status != ResourceStatus.AVAILABLE:
            return False

        query = db.query(Booking).filter(
            Booking.resource_id == resource_id,
            Booking.status.in_([
                BookingStatus.PENDING_APPROVAL,
                BookingStatus.APPROVED
            ]),
            Booking.start_time < end_time,
            Booking.end_time > start_time
        )
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        conflicting_bookings = query.count()
        return conflicting_bookings == 0

    @staticmethod
    def find_available_resources(
        db: Session,
        resource_type: ResourceType,
        start_time: datetime,
        end_time: datetime,
        floor: Optional[int] = None,
        min_capacity: Optional[int] = None
    ) -> List[Resource]:
        query = db.query(Resource).filter(
            Resource.type == resource_type,
            Resource.status == ResourceStatus.AVAILABLE
        )
        if floor is not None:
            query = query.filter(Resource.floor == floor)
        if min_capacity:
            query = query.filter(Resource.capacity >= min_capacity)

        resources = query.order_by(Resource.floor, Resource.hourly_rate).all()

        available_resources = []
        for resource in resources:
            if ResourceService.is_resource_available(db, resource.id, start_time, end_time):
                available_resources.append(resource)

        return available_resources
