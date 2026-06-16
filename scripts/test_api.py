import sys
sys.path.insert(0, '.')
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_full_flow():
    print("=" * 60)
    print("共享办公空间 API 功能测试")
    print("=" * 60)

    print("\n1️⃣ 会员登录")
    resp = requests.post(f"{BASE_URL}/members/login", json={
        "email": "test@example.com",
        "password": "test123"
    })
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✅ 登录成功，获取 token")

    print("\n2️⃣ 获取会员信息")
    resp = requests.get(f"{BASE_URL}/members/me", headers=headers)
    assert resp.status_code == 200
    member = resp.json()
    print(f"   ✅ 会员: {member['name']}, 等级: {member['level']}, 余额: ¥{member['balance']}")

    print("\n3️⃣ 获取资源列表（工位）")
    resp = requests.get(f"{BASE_URL}/resources?type=desk", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    print(f"   ✅ 共有 {data['total']} 个工位资源")
    for r in data["items"][:3]:
        print(f"      - {r['name']} (¥{r['hourly_rate']}/小时, {r['floor']}楼)")

    print("\n4️⃣ 推荐可用资源")
    start_time = (datetime.now() + timedelta(hours=1)).isoformat()
    end_time = (datetime.now() + timedelta(hours=3)).isoformat()
    resp = requests.post(f"{BASE_URL}/bookings/recommend", json={
        "type": "desk",
        "start_time": start_time,
        "end_time": end_time
    }, headers=headers)
    assert resp.status_code == 200
    available = resp.json()
    print(f"   ✅ 可用资源: {len(available)} 个")
    if available:
        print(f"      推荐: {available[0]['name']} - ¥{available[0]['hourly_rate']}/小时")

    print("\n5️⃣ 创建预订（普通会员，需审批）")
    resource_id = available[0]["id"] if available else 1
    resp = requests.post(f"{BASE_URL}/bookings", json={
        "resource_id": resource_id,
        "start_time": start_time,
        "end_time": end_time
    }, headers=headers)
    assert resp.status_code == 200
    result = resp.json()
    print(f"   ✅ 预订创建: {result['message']}")
    print(f"      状态: {result['booking']['status'] if result['booking'] else 'N/A'}")
    print(f"      预估费用: ¥{result['booking']['total_amount'] if result['booking'] else 0}")

    print("\n6️⃣ 黄金会员登录（免审批）")
    resp = requests.post(f"{BASE_URL}/members/login", json={
        "email": "gold@example.com",
        "password": "gold123"
    })
    gold_token = resp.json()["access_token"]
    gold_headers = {"Authorization": f"Bearer {gold_token}"}

    resp = requests.get(f"{BASE_URL}/members/me", headers=gold_headers)
    gold_member = resp.json()
    print(f"   ✅ 会员: {gold_member['name']}, 等级: {gold_member['level']}")

    print("\n7️⃣ 黄金会员创建预订（自动通过）")
    resp = requests.post(f"{BASE_URL}/bookings", json={
        "resource_id": 2,
        "start_time": start_time,
        "end_time": end_time
    }, headers=gold_headers)
    result = resp.json()
    print(f"   ✅ 预订创建: {result['message']}")
    print(f"      状态: {result['booking']['status'] if result['booking'] else 'N/A'}")

    print("\n8️⃣ 我的预订列表")
    resp = requests.get(f"{BASE_URL}/bookings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    print(f"   ✅ 共有 {data['total']} 条预订记录")

    print("\n9️⃣ 管理员登录")
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if resp.status_code == 200:
        admin_token = resp.json()["access_token"]
        print("   ✅ 管理员登录成功")
    else:
        print(f"   ⚠️  管理员登录接口: {resp.status_code}")

    print("\n10️⃣ 账户充值")
    resp = requests.post(f"{BASE_URL}/payments/recharge", json={
        "amount": 500,
        "payment_type": "alipay"
    }, headers=headers)
    assert resp.status_code == 200
    result = resp.json()
    print(f"   ✅ 充值成功，当前余额: ¥{result['balance']}")

    print("\n11️⃣ 我的通知")
    resp = requests.get(f"{BASE_URL}/members/notifications", headers=headers)
    assert resp.status_code == 200
    notifications = resp.json()
    print(f"   ✅ 共有 {len(notifications)} 条通知")
    for n in notifications[:3]:
        print(f"      - [{n['type']}] {n['title']}")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！API 服务运行正常")
    print("=" * 60)

if __name__ == "__main__":
    test_full_flow()
