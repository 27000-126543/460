import requests
import json
from datetime import datetime, timedelta

BASE = "http://localhost:8000/api/v1"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def get(path):
    r = requests.get(f"{BASE}{path}")
    return r.status_code, r.json()

def post(path, data=None, params=None):
    r = requests.post(f"{BASE}{path}", json=data, params=params)
    return r.status_code, r.json()

# ===== 测试1: 设备列表 =====
print_section("1. 设备列表")
code, data = get("/equipments?page_size=20")
print(f"状态码: {code}, 设备总数: {data['total']}")
for eq in data['items'][:3]:
    print(f"  #{eq['id']} {eq['name']} - {eq['type']} - 楼层{eq['floor']} - {eq['status']}")
print(f"  ... (共{data['total']}台)")

# ===== 测试2: 设备数据上报 - 正常 =====
print_section("2. 设备数据上报 - 正常数据")
code, data = post("/equipments/data/report", {
    "equipment_id": 1, "temperature": 50, "current": 5, "is_online": True
})
print(f"状态码: {code}")
print(f"  异常检测: {data['anomaly_detected']}")
print(f"  工单ID: {data['work_order_id']}")

# ===== 测试3: 设备数据上报 - 过热异常 =====
print_section("3. 设备数据上报 - 过热异常(触发工单)")
code, data = post("/equipments/data/report", {
    "equipment_id": 1, "temperature": 95, "current": 8, "is_online": True
})
print(f"状态码: {code}")
print(f"  异常检测: {data['anomaly_detected']}")
print(f"  工单ID: {data['work_order_id']}")
if data['details']:
    for d in data['details']:
        print(f"  - {d['type']}: {d['message']}")

# ===== 测试4: 设备数据上报 - 离线异常 =====
print_section("4. 设备数据上报 - 离线异常(触发工单)")
code, data = post("/equipments/data/report", {
    "equipment_id": 5, "temperature": 25, "current": 0, "is_online": False
})
print(f"状态码: {code}")
print(f"  异常检测: {data['anomaly_detected']}")
print(f"  工单ID: {data['work_order_id']}")

# ===== 测试5: 工单列表 =====
print_section("5. 工单列表")
code, data = get("/work-orders")
print(f"状态码: {code}, 总工单: {data['total']}")
for o in data['items']:
    print(f"  #{o['id']} {o['equipment_name']} - {o['fault_type']}/{o['severity']} - {o['status']} - 工程师:{o['engineer_name']} - 楼层{o['floor']}")

# ===== 测试6: 工程师列表 =====
print_section("6. 工程师列表")
code, data = get("/engineers")
print(f"状态码: {code}")
for e in data['items']:
    print(f"  #{e['id']} {e['name']} - 专长:{e['specialty']} - 负责楼层:{e['floor_range']}")

# ===== 测试7: 工程师接单 =====
print_section("7. 工程师 #1 接单工单 #1")
code, data = post("/work-orders/1/accept", params={"engineer_id": 1})
print(f"状态码: {code}")
print(f"  工单状态: {data.get('status', data)}")

# ===== 测试8: 开始处理 =====
print_section("8. 工程师开始处理工单 #1")
code, data = post("/work-orders/1/start", params={"engineer_id": 1, "remark": "检查散热系统"})
print(f"状态码: {code}")
print(f"  结果: {data.get('message', data)}")

# ===== 测试9: 完成工单 =====
print_section("9. 工程师完成工单 #1")
code, data = post("/work-orders/1/complete", params={"engineer_id": 1, "remark": "更换风扇，温度恢复正常"})
print(f"状态码: {code}")
print(f"  工单状态: {data.get('status', data)}")

# ===== 测试10: 设备状态恢复检查 =====
print_section("10. 设备状态检查(工单完成后应恢复 ONLINE)")
code, data = get("/equipments/1")
print(f"状态码: {code}")
print(f"  设备: {data['name']}")
print(f"  当前状态: {data['status']}")

# ===== 测试11: 日报表 =====
print_section("11. 日报表查询")
today = datetime.now().strftime("%Y-%m-%d")
code, data = get(f"/reports/daily?date={today}")
print(f"状态码: {code}")
print(f"  报表日期: {data['report_date']}")
print(f"  数据可用: {data['data_available']}")
print(f"  总收入: ¥{data['total_revenue']}")
print(f"  整体利用率: {data['overall_utilization_rate']*100:.1f}%")
print(f"  楼层明细: {len(data['floor_utilizations'])} 条")
for fu in data['floor_utilizations']:
    print(f"    {fu['floor']}楼-{fu['resource_type']}: 利用率{fu['utilization_rate']*100:.1f}%, 收入¥{fu['revenue']}")
print(f"  工单统计:")
print(f"    总工单: {data['work_order_stats']['total_orders']}")
print(f"    已完成: {data['work_order_stats']['completed_orders']}")
print(f"    平均响应: {data['work_order_stats']['avg_response_minutes']:.1f} 分钟")

# ===== 测试12: 空日期报表 =====
print_section("12. 空日期报表(无数据也应返回)")
code, data = get("/reports/daily?date=2020-01-01")
print(f"状态码: {code}")
print(f"  报表日期: {data['report_date']}")
print(f"  数据可用: {data['data_available']}")
print(f"  楼层明细数: {len(data['floor_utilizations'])}")

# ===== 测试13: 会员登录获取token =====
print_section("13. 会员登录")
code, data = post("/members/login", {"email": "test@example.com", "password": "test123"})
print(f"状态码: {code}")
member_token = data.get('access_token', '')
member_id = data.get('member_id', '')
print(f"  会员ID: {member_id}")
print(f"  Token: {member_token[:20]}...")

# ===== 测试14: 预订测试 =====
print_section("14. 会员预订工位")
start = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
end = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
headers = {"Authorization": f"Bearer {member_token}"}
r = requests.post(f"{BASE}/bookings", json={
    "resource_id": 1, "start_time": start, "end_time": end
}, headers=headers)
print(f"状态码: {r.status_code}")
booking_data = r.json()
print(f"  预订ID: {booking_data.get('id')}")
print(f"  状态: {booking_data.get('status')}")
print(f"  总金额: ¥{booking_data.get('total_amount')}")

# ===== 测试15: 审批列表 =====
print_section("15. 管理员登录&审批列表")
code, admin_data = post("/admin/login", {"username": "admin", "password": "admin123"})
admin_token = admin_data.get('access_token', '')
admin_headers = {"Authorization": f"Bearer {admin_token}"}
r = requests.get(f"{BASE}/approvals", headers=admin_headers)
approvals = r.json()
print(f"状态码: {r.status_code}, 待审批: {approvals['total']}")
for a in approvals['items'][:3]:
    print(f"  #{a['id']} - 预订ID:{a['booking_id']} - 状态:{a['status']} - 级别:{a['approver_level']}")

# ===== 测试16: 余额限制测试 =====
print_section("16. 余额不足限制预订测试")
# 先把会员余额改成负数
print("  (提示：需要先制造余额不足场景。当前测试验证报表和工单部分)")

# ===== 测试17: Excel导出 =====
print_section("17. Excel报表导出")
r = requests.get(f"{BASE}/reports/daily/export?date={today}")
print(f"状态码: {r.status_code}")
print(f"  Content-Type: {r.headers.get('Content-Type')}")
print(f"  文件大小: {len(r.content)} bytes")
if len(r.content) > 0:
    print("  ✅ Excel文件生成成功")

print("\n" + "="*60)
print("  所有功能测试完成！")
print("="*60)
