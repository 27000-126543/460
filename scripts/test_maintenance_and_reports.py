"""
维修记录 + 运营报表 独立验证脚本
不依赖任何历史数据，脚本自己创建设备、工程师、工单并验证接口返回
"""
import requests
from datetime import datetime, timedelta, date

BASE = "http://localhost:8000/api/v1"
PASSED = 0
FAILED = 0
CREATED = {}


def section(title):
    print(f"\n--- {title} ---")


def test(name, fn):
    global PASSED, FAILED
    try:
        fn()
        print(f"  ✅ {name}")
        PASSED += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        FAILED += 1
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        FAILED += 1


def admin_h():
    r = requests.post(f"{BASE}/admin/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def member_h():
    r = requests.post(f"{BASE}/members/login", json={"email": "test@example.com", "password": "test123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ============================
print("\n" + "=" * 60)
print("  一、维修记录全流程")
print("=" * 60)


def setup_equipment_and_engineer():
    ah = admin_h()
    eq1 = requests.post(f"{BASE}/equipments", headers=ah, json={
        "name": "测试投影仪-1F", "type": "projector", "floor": 1,
        "area": "A区", "location": "1楼A区-测试投影",
        "temp_threshold": 60, "current_threshold": 8
    }).json()
    eq2 = requests.post(f"{BASE}/equipments", headers=ah, json={
        "name": "测试空调-2F", "type": "air_conditioner", "floor": 2,
        "area": "B区", "location": "2楼B区-测试空调",
        "temp_threshold": 45, "current_threshold": 12
    }).json()
    eng = requests.post(f"{BASE}/engineers", headers=ah, json={
        "name": "测试工程师", "phone": "13900001111",
        "specialties": ["projector", "air_conditioner"], "responsible_floors": [1, 2]
    }).json()
    CREATED["eq1_id"] = eq1["id"]
    CREATED["eq2_id"] = eq2["id"]
    CREATED["eng_id"] = eng["id"]


def test_create_work_order_via_anomaly():
    ah = admin_h()
    eq1_id = CREATED["eq1_id"]
    r = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": eq1_id, "temperature": 75, "current": 5, "is_online": True
    })
    assert r.status_code == 200
    d = r.json()
    assert d["anomaly_detected"] == True, f"应该检测到异常: {d}"
    assert d["work_order_id"] is not None, "应该生成工单"
    CREATED["wo1_id"] = d["work_order_id"]


def test_complete_without_work_order_id():
    ah = admin_h()
    wo_id = CREATED["wo1_id"]
    eng_id = CREATED["eng_id"]

    requests.put(f"{BASE}/work-orders/{wo_id}/assign", headers=ah, json={"engineer_id": eng_id})
    requests.post(f"{BASE}/work-orders/{wo_id}/accept?engineer_id={eng_id}", headers=ah)
    requests.post(f"{BASE}/work-orders/{wo_id}/start?engineer_id={eng_id}", headers=ah)

    r = requests.post(
        f"{BASE}/work-orders/{wo_id}/complete?engineer_id={eng_id}",
        headers=ah,
        json={
            "result": "更换灯泡，清洁镜头",
            "materials_used": "灯泡x1",
            "photo_url": "https://example.com/repair1.jpg",
            "needs_recheck": True,
            "recheck_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "remark": "3天后复查"
        }
    )
    assert r.status_code == 200, f"完成工单失败(不传work_order_id): {r.text}"
    d = r.json()
    assert d["success"] == True
    assert d["data"]["maintenance_record"] is not None, "应该返回维修记录"
    CREATED["record1"] = d["data"]["maintenance_record"]


def test_complete_with_mismatch_work_order_id():
    ah = admin_h()
    eq2_id = CREATED["eq2_id"]
    eng_id = CREATED["eng_id"]

    r0 = requests.post(f"{BASE}/equipments/data/report", json={
        "equipment_id": eq2_id, "temperature": 55, "current": 5, "is_online": True
    })
    wo_id = r0.json()["work_order_id"]
    CREATED["wo2_id"] = wo_id

    requests.put(f"{BASE}/work-orders/{wo_id}/assign", headers=ah, json={"engineer_id": eng_id})
    requests.post(f"{BASE}/work-orders/{wo_id}/accept?engineer_id={eng_id}", headers=ah)
    requests.post(f"{BASE}/work-orders/{wo_id}/start?engineer_id={eng_id}", headers=ah)

    r = requests.post(
        f"{BASE}/work-orders/{wo_id}/complete?engineer_id={eng_id}",
        headers=ah,
        json={
            "work_order_id": 99999,
            "result": "测试不一致的工单编号"
        }
    )
    assert r.status_code == 400, f"编号不一致应该返回400: {r.status_code}"
    assert "不一致" in r.json()["detail"], f"错误信息应该提到不一致: {r.json()}"


def test_complete_with_matching_work_order_id():
    ah = admin_h()
    wo_id = CREATED["wo2_id"]
    eng_id = CREATED["eng_id"]

    r = requests.post(
        f"{BASE}/work-orders/{wo_id}/complete?engineer_id={eng_id}",
        headers=ah,
        json={
            "work_order_id": wo_id,
            "result": "充氟清洗",
            "materials_used": "制冷剂x1",
            "needs_recheck": False,
            "remark": "已恢复正常"
        }
    )
    assert r.status_code == 200, f"编号一致应该成功: {r.text}"
    CREATED["record2"] = r.json()["data"]["maintenance_record"]


def test_maintenance_record_has_timestamps():
    for key in ["record1", "record2"]:
        rec = CREATED[key]
        assert rec["created_at"] is not None, f"{key} created_at 不能为空"
        assert rec["updated_at"] is not None, f"{key} updated_at 不能为空"


def test_equipment_maintenance_records():
    ah = admin_h()
    eq1_id = CREATED["eq1_id"]
    r = requests.get(f"{BASE}/equipments/{eq1_id}/maintenance-records", headers=ah)
    assert r.status_code == 200, f"设备维修记录接口失败: {r.text}"
    data = r.json()
    if isinstance(data, list):
        records = data
    else:
        records = data.get("items", [])
    assert len(records) >= 1, f"设备{eq1_id}应该至少有1条维修记录"
    rec = records[0]
    assert rec["created_at"] is not None, "维修记录 created_at 不能为空"
    assert rec["updated_at"] is not None, "维修记录 updated_at 不能为空"
    assert rec["result"] is not None, "维修记录 result 不能为空"


def test_maintenance_record_list():
    ah = admin_h()
    r = requests.get(f"{BASE}/maintenance-records?page=1&page_size=20", headers=ah)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2, f"至少有2条维修记录，实际{data['total']}"
    for rec in data["items"]:
        assert rec["created_at"] is not None, f"记录#{rec['id']} created_at为空"
        assert rec["updated_at"] is not None, f"记录#{rec['id']} updated_at为空"


# ============================
print("\n" + "=" * 60)
print("  二、运营报表对比按维度统计")
print("=" * 60)


def setup_work_orders_for_comparison():
    ah = admin_h()
    eq1_id = CREATED["eq1_id"]
    eq2_id = CREATED["eq2_id"]

    for _ in range(3):
        requests.post(f"{BASE}/equipments/data/report", json={
            "equipment_id": eq1_id, "temperature": 80, "current": 5, "is_online": True
        })
        requests.post(f"{BASE}/equipments/data/report", json={
            "equipment_id": eq2_id, "temperature": 55, "current": 5, "is_online": True
        })
    CREATED["extra_wo_count"] = 6


def test_floor_comparison_different_counts():
    ah = admin_h()
    today = date.today().isoformat()
    r = requests.get(f"{BASE}/reports/comparison/floor?date={today}", headers=ah)
    assert r.status_code == 200
    data = r.json()
    floors = data.get("floor_comparisons", [])
    if len(floors) >= 2:
        counts = {f["floor"]: f["work_order_count"] for f in floors}
        floor_keys = sorted(counts.keys())
        if len(floor_keys) >= 2:
            c1, c2 = counts[floor_keys[0]], counts[floor_keys[1]]
            assert c1 != c2 or (c1 == 0 and c2 == 0), \
                f"不同楼层工单数应该不同: 1F={c1}, 2F={c2} (除非都是0)"
    print(f"    楼层工单数: {[(f['floor'], f['work_order_count']) for f in floors]}")


def test_resource_type_comparison_different_counts():
    ah = admin_h()
    today = date.today().isoformat()
    r = requests.get(f"{BASE}/reports/comparison/resource-type?date={today}", headers=ah)
    assert r.status_code == 200
    data = r.json()
    types = data.get("resource_type_comparisons", [])
    counts = {t["resource_type"]: t["work_order_count"] for t in types}
    print(f"    资源类型工单数: {counts}")
    total_wo = sum(counts.values())
    assert total_wo > 0, f"至少一个资源类型应该有工单, 实际: {counts}"


def test_weekly_report_covers_full_week():
    ah = admin_h()
    today = date.today()
    year, week, _ = today.isocalendar()
    r = requests.get(f"{BASE}/reports/weekly?year={year}&week={week}", headers=ah)
    assert r.status_code == 200
    data = r.json()
    assert data["year"] == year
    assert data["week"] == week
    print(f"    周报工单数: {data['work_order_stats']['total_orders']}")


def test_monthly_report_covers_full_month():
    ah = admin_h()
    today = date.today()
    r = requests.get(f"{BASE}/reports/monthly?year={today.year}&month={today.month}", headers=ah)
    assert r.status_code == 200
    data = r.json()
    assert data["year"] == today.year
    assert data["month"] == today.month
    print(f"    月报工单数: {data['work_order_stats']['total_orders']}")


def test_weekly_excel_export():
    ah = admin_h()
    today = date.today()
    year, week, _ = today.isocalendar()
    r = requests.get(f"{BASE}/reports/weekly/export?year={year}&week={week}", headers=ah)
    assert r.status_code == 200
    assert len(r.content) > 1000, "Excel文件应该大于1000字节"
    print(f"    周报Excel: {len(r.content)} bytes")


def test_monthly_excel_export():
    ah = admin_h()
    today = date.today()
    r = requests.get(f"{BASE}/reports/monthly/export?year={today.year}&month={today.month}", headers=ah)
    assert r.status_code == 200
    assert len(r.content) > 1000, "Excel文件应该大于1000字节"
    print(f"    月报Excel: {len(r.content)} bytes")


def test_trend_endpoints():
    ah = admin_h()
    today = date.today()
    start = (today - timedelta(days=7)).isoformat()
    end = today.isoformat()

    r1 = requests.get(f"{BASE}/reports/trend/utilization?start_date={start}&end_date={end}", headers=ah)
    assert r1.status_code == 200

    r2 = requests.get(f"{BASE}/reports/trend/revenue?start_date={start}&end_date={end}", headers=ah)
    assert r2.status_code == 200

    r3 = requests.get(f"{BASE}/reports/trend/work-orders?start_date={start}&end_date={end}", headers=ah)
    assert r3.status_code == 200
    data3 = r3.json()
    print(f"    工单趋势数据点: {len(data3['data_points'])}")


# ============================
# Run all tests
# ============================

print("\n--- 准备测试数据 ---")
setup_equipment_and_engineer()

section("一、维修记录全流程")
test("异常上报生成工单", test_create_work_order_via_anomaly)
test("完成工单(不传work_order_id)", test_complete_without_work_order_id)
test("完成工单(编号不一致→400)", test_complete_with_mismatch_work_order_id)
test("完成工单(编号一致→兼容)", test_complete_with_matching_work_order_id)
test("维修记录时间字段完整", test_maintenance_record_has_timestamps)
test("设备维修记录列表", test_equipment_maintenance_records)
test("全量维修记录列表", test_maintenance_record_list)

section("二、运营报表对比按维度统计")
test("创建对比用工单数据", setup_work_orders_for_comparison)
test("楼层对比工单数有差异", test_floor_comparison_different_counts)
test("资源类型对比工单数有差异", test_resource_type_comparison_different_counts)
test("周报覆盖整周", test_weekly_report_covers_full_week)
test("月报覆盖整月", test_monthly_report_covers_full_month)
test("周报Excel导出", test_weekly_excel_export)
test("月报Excel导出", test_monthly_excel_export)
test("趋势接口", test_trend_endpoints)

print(f"\n{'=' * 60}")
print(f"  总结: {PASSED} 通过, {FAILED} 失败")
print(f"{'=' * 60}")
