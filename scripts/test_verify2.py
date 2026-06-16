import requests
BASE = 'http://localhost:8000/api/v1'

r = requests.post(f'{BASE}/admin/login', json={'username': 'admin', 'password': 'admin123'})
a_h = {'Authorization': f'Bearer {r.json()["access_token"]}'}

print("=== 1. 异常分级验证 ===")
# 设备1: temp_thr=70, current_thr=10
# 温度77度 = 1.1倍 → MEDIUM
r1 = requests.post(f'{BASE}/equipments/data/report', json={
    'equipment_id': 1, 'temperature': 77, 'current': 5, 'is_online': True
})
d1 = r1.json()
print(f"温度77°(1.1倍): anomaly={d1['anomaly_detected']}, wo={d1['work_order_id']}")
wo_id1 = d1['work_order_id']

# 多故障：温度80+电流16+离线
r2 = requests.post(f'{BASE}/equipments/data/report', json={
    'equipment_id': 2, 'temperature': 80, 'current': 16, 'is_online': False
})
d2 = r2.json()
print(f"温度80°+电流16A+离线: anomaly={d2['anomaly_detected']}, details={len(d2['details'])}, wo={d2['work_order_id']}")
wo_id2 = d2['work_order_id']

# 看工单详情严重程度
if wo_id1:
    r3 = requests.get(f'{BASE}/work-orders/{wo_id1}', headers=a_h)
    wo = r3.json()
    print(f"  工单#{wo_id1}: severity={wo.get('severity')}, fault={wo.get('fault_type')}")

if wo_id2:
    r4 = requests.get(f'{BASE}/work-orders/{wo_id2}', headers=a_h)
    wo2 = r4.json()
    print(f"  工单#{wo_id2}: severity={wo2.get('severity')}, fault={wo2.get('fault_type')}")

print("\n=== 2. 维修记录验证 ===")
if wo_id1:
    r = requests.post(f'{BASE}/work-orders/{wo_id1}/assign',
                      headers=a_h, json={'engineer_id': 1})
    print(f"分配工程师: {r.status_code} {r.text[:100]}")

    r = requests.post(f'{BASE}/work-orders/{wo_id1}/accept', headers=a_h)
    print(f"接单: {r.status_code} {r.text[:100]}")

    r = requests.post(f'{BASE}/work-orders/{wo_id1}/start', headers=a_h)
    print(f"开始处理: {r.status_code} {r.text[:100]}")

    r = requests.post(f'{BASE}/work-orders/{wo_id1}/complete', headers=a_h, json={
        'result': '更换滤网，清洁内部',
        'materials_used': '滤网x1, 清洁剂x1',
        'photo_url': 'https://example.com/photo.jpg',
        'needs_recheck': True,
        'recheck_date': '2026-06-23T10:00:00',
        'remark': '运行正常'
    })
    print(f"完成工单: {r.status_code}")
    print(f"  响应: {r.text[:400]}")

    r5 = requests.get(f'{BASE}/equipments/1/maintenance-records', headers=a_h)
    print(f"设备维修记录: {r5.status_code}")
    d5 = r5.json()
    if isinstance(d5, list):
        print(f"  记录数: {len(d5)}")
    else:
        print(f"  keys: {list(d5.keys())[:3]}")

    r6 = requests.get(f'{BASE}/maintenance-records?page=1&page_size=10', headers=a_h)
    print(f"维修记录列表: {r6.status_code}")
else:
    print("没有工单可测试")

print("\n✅ 验证完成")
