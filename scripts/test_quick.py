import requests
from datetime import datetime, timedelta

BASE = 'http://localhost:8000/api/v1'

# 会员登录
r = requests.post(f'{BASE}/members/login', json={'email': 'test@example.com', 'password': 'test123'})
m_token = r.json()['access_token']
m_headers = {'Authorization': f'Bearer {m_token}'}

# 管理员登录
r = requests.post(f'{BASE}/admin/login', json={'username': 'admin', 'password': 'admin123'})
a_token = r.json()['access_token']
a_headers = {'Authorization': f'Bearer {a_token}'}

# 审批列表
r = requests.get(f'{BASE}/approvals?status=pending', headers=a_headers)
print('审批列表 status_code:', r.status_code)
data = r.json()
print('审批列表类型:', type(data).__name__)

if isinstance(data, list):
    items = data
else:
    items = data.get('approvals') or data.get('items') or []
print(f'待审批数量: {len(items)}')

# 直接列出来看看
for i, item in enumerate(items[:3]):
    print(f'  [{i}] id={item["id"]}, booking_id={item["booking_id"]}, status={item["status"]}')

# 创建一个新的预订（用 resource_id=7，确保没被订过）
print('\n创建一个新的预订...')
start = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
end = (datetime.now() + timedelta(days=20, hours=2)).strftime("%Y-%m-%d %H:%M:%S")
r = requests.post(f'{BASE}/bookings', json={
    'resource_id': 7, 'start_time': start, 'end_time': end
}, headers=m_headers)
print(f'创建预订: {r.status_code}')
data = r.json()
print('返回:', data)

if data.get('success'):
    booking_id = data['booking']['id']
    print(f'booking_id = {booking_id}')
    
    # 用 booking_id 当 approval_id 来审批
    print(f'\n用 booking_id={booking_id} 当 approval_id 测试审批:')
    r2 = requests.post(f'{BASE}/approvals/{booking_id}/approve', 
                       headers=a_headers, json={'remark': '同意'})
    print(f'审批结果: {r2.status_code}, {r2.text[:200]}')
