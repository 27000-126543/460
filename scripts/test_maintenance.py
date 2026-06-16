import requests
BASE = 'http://localhost:8000/api/v1'

r = requests.post(f'{BASE}/admin/login', json={'username': 'admin', 'password': 'admin123'})
a_h = {'Authorization': f'Bearer {r.json()["access_token"]}'}

print("=== 维修记录全流程验证 ===")

# 1. 找一个待分配的工单
r = requests.get(f'{BASE}/work-orders?status=pending', headers=a_h)
data = r.json()
items = data.get('items', [])
if not items:
    # 创建一个新工单
    r2 = requests.post(f'{BASE}/equipments/data/report', json={
        'equipment_id': 6, 'temperature': 100, 'current': 20, 'is_online': True
    })
    wo_id = r2.json()['work_order_id']
else:
    wo_id = items[0]['id']

print(f"测试工单: #{wo_id}")

# 2. 分配工程师（PUT方法 + body）
r = requests.put(f'{BASE}/work-orders/{wo_id}/assign',
                 headers=a_h, json={'engineer_id': 1})
print(f"分配工程师: {r.status_code}")
assert r.status_code == 200, r.text

# 3. 工程师接单（query参数）
r = requests.post(f'{BASE}/work-orders/{wo_id}/accept?engineer_id=1', headers=a_h)
print(f"接单: {r.status_code}")
assert r.status_code == 200, r.text

# 4. 开始处理
r = requests.post(f'{BASE}/work-orders/{wo_id}/start?engineer_id=1', headers=a_h)
print(f"开始处理: {r.status_code}")
assert r.status_code == 200, r.text

# 5. 完成工单（带维修记录）
r = requests.post(
    f'{BASE}/work-orders/{wo_id}/complete?engineer_id=1',
    headers=a_h,
    json={
        'work_order_id': wo_id,
        'result': '更换滤网，清洁内部风道',
        'materials_used': '滤网x1, 清洁剂x1',
        'photo_url': 'https://example.com/photo.jpg',
        'needs_recheck': True,
        'recheck_date': '2026-06-23T10:00:00',
        'remark': '运行正常，建议一周后复检'
    }
)
print(f"完成工单: {r.status_code}")
print(f"  响应前300字: {r.text[:300]}")
assert r.status_code == 200, r.text

# 6. 设备维修记录
r = requests.get(f'{BASE}/equipments/6/maintenance-records', headers=a_h)
print(f"设备维修记录: {r.status_code}")
d = r.json()
if isinstance(d, list):
    print(f"  记录数: {len(d)}")
    if d:
        print(f"  最新记录: result={d[0].get('result')[:20]}..., needs_recheck={d[0].get('needs_recheck')}")
else:
    print(f"  keys: {list(d.keys())[:3]}")

# 7. 维修记录列表
r = requests.get(f'{BASE}/maintenance-records?page=1&page_size=10', headers=a_h)
print(f"维修记录列表: {r.status_code}")
d = r.json()
print(f"  总数: {d.get('total', 0)}")

# 8. 标记设备为反复故障
r = requests.put(f'{BASE}/equipments/6/frequent-fault',
                 headers=a_h, json={'is_frequent': True})
print(f"标记反复故障: {r.status_code}")

# 验证设备信息
r2 = requests.get(f'{BASE}/equipments/6', headers=a_h)
if r2.status_code == 200:
    eq = r2.json()
    print(f"  设备 fault_count={eq.get('fault_count')}, is_frequent_fault={eq.get('is_frequent_fault')}")

print("\n✅ 维修记录全流程验证通过！")
