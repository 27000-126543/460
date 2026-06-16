import requests
import json
from datetime import datetime, timedelta
import sys

BASE = "http://localhost:8000/api/v1"

passed = 0
failed = 0
tests = []

def test(name):
    def decorator(func):
        tests.append((name, func))
        return func
    return decorator

def run_tests():
    global passed, failed
    for name, func in tests:
        try:
            func()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# 全局变量
member_token = None
member_id = None
member_headers = {}
booking_id = None
admin_token = None
admin_headers = {}

# ===== 设备管理 =====
section("一、设备管理")

@test("设备列表查询")
def _():
    r = requests.get(f"{BASE}/equipments", params={"page_size": 20})
    assert r.status_code == 200, f"状态码: {r.status_code}"
    data = r.json()
    assert data["total"] >= 10
    assert len(data["items"]) > 0

@test("设备详情查询")
def _():
    r = requests.get(f"{BASE}/equipments/1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert "name" in data

@test("上报正常数据-无异常")
def _():
    r = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 4, "temperature": 30, "current": 3, "is_online": True
    })
    assert r.status_code == 200
    data = r.json()
    assert data["anomaly_detected"] == False
    assert data["work_order_id"] is None

@test("上报温度异常-触发生成工单")
def _():
    r = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 4, "temperature": 90, "current": 5, "is_online": True
    })
    assert r.status_code == 200
    data = r.json()
    assert data["anomaly_detected"] == True
    assert data["work_order_id"] is not None
    assert len(data["details"]) > 0
    assert data["details"][0]["type"] == "overheat"

@test("上报离线异常-触发生成工单")
def _():
    r = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 8, "temperature": 25, "current": 0, "is_online": False
    })
    assert r.status_code == 200
    data = r.json()
    assert data["anomaly_detected"] == True
    assert data["work_order_id"] is not None

@test("设备状态-异常后变为故障")
def _():
    r = requests.get(f"{BASE}/equipments/4")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "malfunction"

# ===== 工单管理 =====
section("二、工单管理")

@test("工单列表查询")
def _():
    r = requests.get(f"{BASE}/work-orders")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert "equipment_name" in data["items"][0]
    assert "engineer_name" in data["items"][0]

@test("工单详情查询")
def _():
    r = requests.get(f"{BASE}/work-orders/1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert "equipment_name" in data

@test("工程师列表")
def _():
    r = requests.get(f"{BASE}/engineers")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 3

test_order_id = None
test_engineer_id = None
completed_eq_id = None

@test("工程师接单")
def _():
    global test_order_id, test_engineer_id
    r = requests.get(f"{BASE}/work-orders", params={"status": "assigned"})
    items = r.json()["items"]
    assert len(items) > 0, "没有已分配的工单可测试"
    order = items[0]
    test_order_id = order["id"]
    test_engineer_id = order["engineer_id"]
    
    r = requests.post(f"{BASE}/work-orders/{test_order_id}/accept",
                     params={"engineer_id": test_engineer_id})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    assert data["data"]["status"] == "accepted"

@test("开始处理工单")
def _():
    r = requests.post(f"{BASE}/work-orders/{test_order_id}/start",
                     params={"engineer_id": test_engineer_id, "remark": "开始检查"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True

@test("完成工单")
def _():
    global completed_eq_id
    r = requests.post(f"{BASE}/work-orders/{test_order_id}/complete",
                     params={"engineer_id": test_engineer_id, "remark": "问题解决"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    assert data["data"]["status"] == "completed"
    completed_eq_id = data["data"]["equipment_id"]

@test("工单完成后设备恢复在线")
def _():
    r = requests.get(f"{BASE}/equipments/{completed_eq_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "online"

# ===== 报表管理 =====
section("三、运营报表")

today_str = datetime.now().strftime("%Y-%m-%d")

@test("日报表查询-有数据")
def _():
    r = requests.get(f"{BASE}/reports/daily", params={"date": today_str})
    assert r.status_code == 200, f"状态码: {r.status_code}, {r.text[:200]}"
    data = r.json()
    assert data["report_date"] == today_str
    assert "floor_utilizations" in data
    assert "work_order_stats" in data
    assert "total_revenue" in data

@test("日报表查询-空日期(返回空报表)")
def _():
    r = requests.get(f"{BASE}/reports/daily", params={"date": "2020-01-01"})
    assert r.status_code == 200
    data = r.json()
    assert data["data_available"] == False
    assert isinstance(data["floor_utilizations"], list)

@test("日报表查询-日期格式错误")
def _():
    r = requests.get(f"{BASE}/reports/daily", params={"date": "invalid-date"})
    assert r.status_code == 400

@test("Excel报表导出")
def _():
    r = requests.get(f"{BASE}/reports/daily/export", params={"date": today_str})
    assert r.status_code == 200, f"状态码: {r.status_code}, {r.text[:200]}"
    assert "application/vnd.openxmlformats" in r.headers["Content-Type"]
    assert len(r.content) > 1000

@test("日期范围报表查询")
def _():
    r = requests.get(f"{BASE}/reports/range", params={
        "start_date": "2020-01-01", "end_date": "2020-01-03"
    })
    assert r.status_code == 200
    data = r.json()
    assert "reports" in data
    assert len(data["reports"]) == 3

# ===== 预订&余额限制 =====
section("四、预订结算与余额限制")

@test("会员登录")
def _():
    global member_token, member_id, member_headers
    r = requests.post(f"{BASE}/members/login", json={
        "email": "test@example.com", "password": "test123"
    })
    assert r.status_code == 200
    data = r.json()
    member_token = data["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}
    assert member_token
    # 用 /me 获取会员ID
    r2 = requests.get(f"{BASE}/members/me", headers=member_headers)
    assert r2.status_code == 200
    member_id = r2.json()["id"]
    assert member_id

@test("会员初始状态-未限制")
def _():
    r = requests.get(f"{BASE}/members/me", headers=member_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["booking_restricted"] == False

@test("普通会员预订-需审批")
def _():
    global booking_id
    start = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    end = (datetime.now() + timedelta(days=5, hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    r = requests.post(f"{BASE}/bookings", json={
        "resource_id": 3, "start_time": start, "end_time": end
    }, headers=member_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    assert data["booking"]["status"] == "pending_approval"
    booking_id = data["booking"]["id"]

@test("管理员登录")
def _():
    global admin_token, admin_headers
    r = requests.post(f"{BASE}/admin/login", json={
        "username": "admin", "password": "admin123"
    })
    assert r.status_code == 200
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

@test("审批通过预订")
def _():
    r = requests.post(f"{BASE}/approvals/{booking_id}/approve",
                      headers=admin_headers, json={"remark": "同意"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True

@test("签到")
def _():
    r = requests.post(f"{BASE}/bookings/{booking_id}/check-in",
                     headers=member_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True

@test("签退-正常结算")
def _():
    r = requests.post(f"{BASE}/bookings/{booking_id}/check-out",
                     headers=member_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    assert data["booking"]["status"] == "completed"

@test("充值后余额正常-未限制")
def _():
    # 先充值
    r = requests.post(f"{BASE}/payments/recharge",
                     json={"member_id": member_id, "amount": 1000},
                     headers=admin_headers)
    assert r.status_code == 200
    # 再查状态
    r2 = requests.get(f"{BASE}/members/me", headers=member_headers)
    data = r2.json()
    assert data["booking_restricted"] == False
    assert data["balance"] > 0

# ===== 调度器 =====
section("五、后台调度任务")

@test("审批超时检查函数可调用")
def _():
    from app.services.approval_service import ApprovalService
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        count = ApprovalService.check_timeout_and_escalate(db)
        assert isinstance(count, int)
    finally:
        db.close()

@test("工单超时检查函数可调用")
def _():
    from app.services.work_order_service import WorkOrderService
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        count = WorkOrderService.check_timeout_and_escalate(db)
        assert isinstance(count, int)
    finally:
        db.close()

@test("审批支持多级升级")
def _():
    from app.models import Approval, ApprovalStatus, Admin
    from app.services.approval_service import ApprovalService
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # 找一个审批，验证 escalated 状态存在
        approvals = db.query(Approval).all()
        assert len(approvals) > 0
        # 验证有多个管理员级别
        admins = db.query(Admin).all()
        levels = set(a.level for a in admins)
        assert len(levels) >= 2, "至少需要两级管理员才能验证升级"
    finally:
        db.close()

# ===== 运行测试 =====
run_tests()

# ===== 总结 =====
section("测试总结")
print(f"  通过: {passed}")
print(f"  失败: {failed}")
print(f"  总计: {passed + failed}")

if failed > 0:
    sys.exit(1)
else:
    print("\n  🎉 所有测试通过！")
