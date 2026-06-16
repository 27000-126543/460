"""快速验证5个新增功能模块"""
import requests
from datetime import datetime, timedelta

BASE = "http://localhost:8000/api/v1"
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1

# === 登录 ===
r = requests.post(f"{BASE}/members/login", json={"email": "test@example.com", "password": "test123"})
m_token = r.json()["access_token"]
m_h = {"Authorization": f"Bearer {m_token}"}

r = requests.post(f"{BASE}/admin/login", json={"username": "admin", "password": "admin123"})
a_token = r.json()["access_token"]
a_h = {"Authorization": f"Bearer {a_token}"}

print("\n=== 1. 异常分级算法 ===")

def test_anomaly_severity():
    # 设备1的阈值：temp_threshold=40, current_threshold=10
    # 测试温度刚超阈值（1.0-1.2倍）→ MEDIUM
    r = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 1, "temperature": 44, "current": 5, "is_online": True
    })
    assert r.status_code == 200
    data = r.json()
    # 44/40 = 1.1倍 → MEDIUM
    print(f"    温度超1.1倍: 异常={data['is_anomaly']}, 工单={data.get('work_order_id')}")
    if data.get('severity'):
        assert data['severity'] == 'medium', f"预期medium, 实际{data['severity']}"

    # 测试温度超1.5倍 → CRITICAL
    r2 = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 2, "temperature": 65, "current": 5, "is_online": True
    })
    assert r2.status_code == 200
    data2 = r2.json()
    print(f"    温度超1.6倍: 异常={data2['is_anomaly']}")
    if data2.get('severity'):
        assert data2['severity'] == 'critical', f"预期critical, 实际{data2['severity']}"

    # 测试离线 → HIGH
    r3 = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": 3, "temperature": 25, "current": 0, "is_online": False
    })
    assert r3.status_code == 200
    data3 = r3.json()
    print(f"    离线: 异常={data3['is_anomaly']}")
    if data3.get('severity'):
        assert data3['severity'] == 'high', f"预期high, 实际{data3['severity']}"

test("异常分级（温度/电流/离线）", test_anomaly_severity)

print("\n=== 2. 维修记录 ===")

def test_maintenance_record():
    # 获取一个已分配的工单
    r = requests.get(f"{BASE}/work-orders?status=pending", headers=a_h)
    assert r.status_code == 200
    data = r.json()
    wo_id = None
    if isinstance(data, list):
        items = data
    else:
        items = data.get('items', data.get('work_orders', []))
    if items:
        wo_id = items[0]['id']
    
    if not wo_id:
        # 创建一个新的工单用于测试
        r = requests.post(f"{BASE}/equipments/data/report", json={
            "equipment_id": 5, "temperature": 70, "current": 15, "is_online": True
        })
        wo_id = r.json().get('work_order_id')
    
    assert wo_id, "没有找到工单"
    print(f"    测试工单: #{wo_id}")

    # 分配工程师
    r = requests.post(f"{BASE}/work-orders/{wo_id}/assign", 
                      headers=a_h, json={"engineer_id": 1})
    assert r.status_code == 200

    # 工程师接单
    eng_r = requests.get(f"{BASE}/engineers", headers=a_h)
    print(f"    工程师列表状态: {eng_r.status_code}")
    
    r2 = requests.post(f"{BASE}/work-orders/{wo_id}/accept", headers=a_h)
    print(f"    接单: {r2.status_code}")

    # 开始处理
    r3 = requests.post(f"{BASE}/work-orders/{wo_id}/start", headers=a_h)
    print(f"    开始处理: {r3.status_code}")

    # 完成工单（带维修记录）
    r4 = requests.post(f"{BASE}/work-orders/{wo_id}/complete", headers=a_h, json={
        "result": "更换滤网，清洁内部",
        "materials_used": "滤网x1, 清洁剂x1",
        "photo_url": "https://example.com/photo.jpg",
        "needs_recheck": True,
        "recheck_date": "2026-06-23T10:00:00",
        "remark": "运行正常"
    })
    print(f"    完成工单: {r4.status_code}")
    print(f"    响应: {r4.text[:200]}")
    assert r4.status_code == 200, f"完成工单失败: {r4.text}"

    # 查看设备维修记录
    r5 = requests.get(f"{BASE}/equipments/5/maintenance-records", headers=a_h)
    print(f"    设备维修记录: {r5.status_code}")
    assert r5.status_code == 200

    # 查看维修记录列表
    r6 = requests.get(f"{BASE}/maintenance-records?page=1&page_size=10", headers=a_h)
    print(f"    维修记录列表: {r6.status_code}")
    assert r6.status_code == 200

test("维修记录全流程", test_maintenance_record)

print("\n=== 3. 报表扩展 ===")

def test_reports():
    # 周报表
    r = requests.get(f"{BASE}/reports/weekly?year=2026&week=25", headers=a_h)
    assert r.status_code == 200
    print(f"    周报表: {r.status_code}")
    
    # 月报表
    r2 = requests.get(f"{BASE}/reports/monthly?year=2026&month=6", headers=a_h)
    assert r2.status_code == 200
    print(f"    月报表: {r2.status_code}")
    
    # 利用率趋势
    r3 = requests.get(f"{BASE}/reports/trend/utilization?start_date=2026-06-01&end_date=2026-06-30", headers=a_h)
    assert r3.status_code == 200
    print(f"    利用率趋势: {r3.status_code}")
    
    # 收入趋势
    r4 = requests.get(f"{BASE}/reports/trend/revenue?start_date=2026-06-01&end_date=2026-06-30", headers=a_h)
    assert r4.status_code == 200
    print(f"    收入趋势: {r4.status_code}")
    
    # 工单趋势
    r5 = requests.get(f"{BASE}/reports/trend/work-orders?start_date=2026-06-01&end_date=2026-06-30", headers=a_h)
    assert r5.status_code == 200
    print(f"    工单趋势: {r5.status_code}")
    
    # 楼层对比
    r6 = requests.get(f"{BASE}/reports/comparison/floor?date=2026-06-16", headers=a_h)
    assert r6.status_code == 200
    print(f"    楼层对比: {r6.status_code}")
    
    # 资源类型对比
    r7 = requests.get(f"{BASE}/reports/comparison/resource-type?date=2026-06-16", headers=a_h)
    assert r7.status_code == 200
    print(f"    资源类型对比: {r7.status_code}")
    
    # 周报表Excel导出
    r8 = requests.get(f"{BASE}/reports/weekly/export?year=2026&week=25", headers=a_h)
    assert r8.status_code == 200
    assert len(r8.content) > 1000
    print(f"    周报表Excel: {len(r8.content)} bytes")
    
    # 月报表Excel导出
    r9 = requests.get(f"{BASE}/reports/monthly/export?year=2026&month=6", headers=a_h)
    assert r9.status_code == 200
    assert len(r9.content) > 1000
    print(f"    月报表Excel: {len(r9.content)} bytes")

test("周/月报表+趋势+对比+Excel", test_reports)

print("\n=== 4. 通知系统 ===")

def test_notifications():
    # 会员通知列表
    r = requests.get(f"{BASE}/members/notifications?page=1&page_size=10", headers=m_h)
    assert r.status_code == 200
    data = r.json()
    print(f"    会员通知列表: {len(data.get('items', [])) if isinstance(data, dict) else len(data)} 条")
    
    # 会员未读数量
    r2 = requests.get(f"{BASE}/members/notifications/unread-count", headers=m_h)
    assert r2.status_code == 200
    print(f"    会员未读: {r2.json()}")
    
    # 管理员通知列表
    r3 = requests.get(f"{BASE}/admin/notifications?page=1&page_size=10", headers=a_h)
    assert r3.status_code == 200
    data3 = r3.json()
    items3 = data3.get('items', []) if isinstance(data3, dict) else data3
    print(f"    管理员通知列表: {len(items3)} 条")
    
    # 管理员未读数量
    r4 = requests.get(f"{BASE}/admin/notifications/unread-count", headers=a_h)
    assert r4.status_code == 200
    print(f"    管理员未读: {r4.json()}")
    
    # 按类型筛选
    r5 = requests.get(f"{BASE}/admin/notifications?type=approval&page=1&page_size=10", headers=a_h)
    assert r5.status_code == 200
    print(f"    按类型筛选(approval): {r5.status_code}")
    
    # 批量标记已读
    if items3 and len(items3) > 0:
        ids = [items3[0]['id']]
        r6 = requests.post(f"{BASE}/admin/notifications/read-batch", 
                          headers=a_h, json={"ids": ids})
        assert r6.status_code == 200
        print(f"    批量标记已读: {r6.status_code}")
    
    # 全部标记已读
    r7 = requests.post(f"{BASE}/members/notifications/read-all", headers=m_h)
    assert r7.status_code == 200
    print(f"    会员全部已读: {r7.status_code}")

test("通知列表+筛选+批量标记已读", test_notifications)

print("\n=== 5. 审批接口兼容 ===")

def test_approval_compat():
    # 创建一个需要审批的预订
    start = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    end = (datetime.now() + timedelta(days=15, hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    r = requests.post(f"{BASE}/bookings", json={
        "resource_id": 4, "start_time": start, "end_time": end
    }, headers=m_h)
    assert r.status_code == 200
    booking_id = r.json()["booking"]["id"]
    print(f"    创建预订 #{booking_id}")

    # 找到对应的审批
    r2 = requests.get(f"{BASE}/approvals?status=pending", headers=a_h)
    items = r2.json() if isinstance(r2.json(), list) else r2.json().get('items', [])
    approval_id = None
    for a in items:
        if a['booking_id'] == booking_id:
            approval_id = a['id']
            break
    
    assert approval_id, "没找到审批"
    print(f"    审批 #{approval_id}")

    # 只传remark，不传action
    r3 = requests.post(f"{BASE}/approvals/{approval_id}/approve",
                       headers=a_h, json={"remark": "只传备注也能通过"})
    assert r3.status_code == 200, f"只传remark失败: {r3.text}"
    print(f"    只传remark通过: {r3.status_code}")

test("审批接口兼容（只传remark）", test_approval_compat)

print(f"\n=== 总结: {passed} 通过, {failed} 失败 ===")
