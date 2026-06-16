import requests

BASE = 'http://localhost:8000/api/v1'

r = requests.post(f'{BASE}/members/login', json={'email': 'test@example.com', 'password': 'test123'})
m_token = r.json()['access_token']
m_headers = {'Authorization': f'Bearer {m_token}'}

r = requests.post(f'{BASE}/admin/login', json={'username': 'admin', 'password': 'admin123'})
a_token = r.json()['access_token']
a_headers = {'Authorization': f'Bearer {a_token}'}

print('=== 会员通知接口测试 ===')

r = requests.get(f'{BASE}/members/notifications', headers=m_headers)
print('会员通知列表:', r.status_code)
data = r.json()
print(f'  keys: {list(data.keys())}')
print(f'  total: {data.get("total")}, page: {data.get("page")}, page_size: {data.get("page_size")}')
print(f'  items count: {len(data.get("items", []))}')

r = requests.get(f'{BASE}/members/notifications?type=booking', headers=m_headers)
print('会员通知列表(筛选type=booking):', r.status_code)

r = requests.get(f'{BASE}/members/notifications?is_read=false', headers=m_headers)
print('会员通知列表(筛选未读):', r.status_code)

r = requests.get(f'{BASE}/members/notifications/unread-count', headers=m_headers)
print('会员未读数量:', r.status_code, r.json())

r = requests.post(f'{BASE}/members/notifications/read-all', headers=m_headers)
print('会员全部标记已读:', r.status_code, r.json())

print()
print('=== 管理员通知接口测试 ===')

r = requests.get(f'{BASE}/admin/notifications', headers=a_headers)
print('管理员通知列表:', r.status_code)
data = r.json()
print(f'  keys: {list(data.keys())}')
print(f'  total: {data.get("total")}, page: {data.get("page")}, page_size: {data.get("page_size")}')
print(f'  items count: {len(data.get("items", []))}')

r = requests.get(f'{BASE}/admin/notifications/unread-count', headers=a_headers)
print('管理员未读数量:', r.status_code, r.json())

r = requests.post(f'{BASE}/admin/notifications/read-batch', headers=a_headers, json={'ids': [1, 2, 3]})
print('管理员批量标记已读:', r.status_code, r.json())

print()
print('=== 审批接口兼容测试 ===')

r = requests.get(f'{BASE}/approvals?status=pending', headers=a_headers)
items = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
print(f'待审批数量: {len(items)}')

if items:
    approval_id = items[0]['id']
    r = requests.post(f'{BASE}/approvals/{approval_id}/reject', headers=a_headers, json={'remark': '测试拒绝'})
    print('拒绝审批(只传remark):', r.status_code, r.json())

print()
print('所有测试完成!')
