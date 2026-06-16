import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Admin, Resource, ResourceType, ResourceStatus, Member, MemberLevel
from app.utils import hash_password


def init_database():
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

    db = SessionLocal()

    try:
        admin1 = db.query(Admin).filter(Admin.username == "admin").first()
        if not admin1:
            admin1 = Admin(
                username="admin",
                name="系统管理员",
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                level=1
            )
            db.add(admin1)
            print("创建一级管理员: admin / admin123")

        admin2 = db.query(Admin).filter(Admin.username == "superadmin").first()
        if not admin2:
            admin2 = Admin(
                username="superadmin",
                name="超级管理员",
                email="superadmin@example.com",
                password_hash=hash_password("super123"),
                level=2
            )
            db.add(admin2)
            print("创建二级管理员: superadmin / super123")

        resources_data = [
            {"name": "A区-工位01", "type": ResourceType.DESK, "floor": 1, "area": "A区", "hourly_rate": 10, "capacity": 1},
            {"name": "A区-工位02", "type": ResourceType.DESK, "floor": 1, "area": "A区", "hourly_rate": 10, "capacity": 1},
            {"name": "A区-工位03", "type": ResourceType.DESK, "floor": 1, "area": "A区", "hourly_rate": 10, "capacity": 1},
            {"name": "B区-工位01", "type": ResourceType.DESK, "floor": 2, "area": "B区", "hourly_rate": 15, "capacity": 1},
            {"name": "B区-工位02", "type": ResourceType.DESK, "floor": 2, "area": "B区", "hourly_rate": 15, "capacity": 1},
            {"name": "会议室-小", "type": ResourceType.MEETING_ROOM, "floor": 1, "area": "A区", "hourly_rate": 50, "capacity": 6},
            {"name": "会议室-中", "type": ResourceType.MEETING_ROOM, "floor": 2, "area": "B区", "hourly_rate": 100, "capacity": 15},
            {"name": "会议室-大", "type": ResourceType.MEETING_ROOM, "floor": 3, "area": "C区", "hourly_rate": 200, "capacity": 30},
        ]

        for res_data in resources_data:
            existing = db.query(Resource).filter(Resource.name == res_data["name"]).first()
            if not existing:
                resource = Resource(**res_data, status=ResourceStatus.AVAILABLE)
                db.add(resource)
                print(f"创建资源: {res_data['name']}")

        test_member = db.query(Member).filter(Member.email == "test@example.com").first()
        if not test_member:
            test_member = Member(
                name="测试会员",
                email="test@example.com",
                phone="13800138000",
                password_hash=hash_password("test123"),
                level=MemberLevel.BASIC,
                credit_limit=1000,
                balance=500
            )
            db.add(test_member)
            print("创建测试会员: test@example.com / test123")

        gold_member = db.query(Member).filter(Member.email == "gold@example.com").first()
        if not gold_member:
            gold_member = Member(
                name="黄金会员",
                email="gold@example.com",
                phone="13900139000",
                password_hash=hash_password("gold123"),
                level=MemberLevel.GOLD,
                credit_limit=8000,
                balance=2000
            )
            db.add(gold_member)
            print("创建黄金会员: gold@example.com / gold123 (免审批)")

        db.commit()
        print("\n初始化数据完成！")

    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
