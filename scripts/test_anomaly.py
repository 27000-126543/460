import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.equipment_service import EquipmentService
from app.models import FaultSeverity

print('Services imported successfully!')
print()

class MockEquipment:
    temp_threshold = 100.0
    current_threshold = 10.0

eq = MockEquipment()

print('=== 异常分级算法测试 ===')

test_cases = [
    ('温度 1.01倍 (刚超阈值)', 101.0, None, True, 'medium'),
    ('温度 1.1倍', 110.0, None, True, 'medium'),
    ('温度 1.2倍 (边界)', 120.0, None, True, 'high'),
    ('温度 1.3倍', 130.0, None, True, 'high'),
    ('温度 1.5倍 (边界)', 150.0, None, True, 'critical'),
    ('温度 2.0倍', 200.0, None, True, 'critical'),
    ('电流 1.1倍', None, 11.0, True, 'medium'),
    ('电流 1.2倍 (边界)', None, 12.0, True, 'high'),
    ('电流 1.5倍 (边界)', None, 15.0, True, 'critical'),
    ('离线', None, None, False, 'high'),
    ('温度2倍 + 离线', 200.0, None, False, 'critical'),
    ('温度1.3倍 + 电流1.1倍', 130.0, 11.0, True, 'high'),
]

all_passed = True
for name, temp, current, online, expected in test_cases:
    is_anomaly, details, severity = EquipmentService.detect_anomaly(None, eq, temp, current, online)
    passed = severity.value == expected
    status = 'PASS' if passed else 'FAIL'
    if not passed:
        all_passed = False
    print(f'[{status}] {name}: severity={severity.value} (expected={expected})')

print()
print('=== FaultSeverity priority 测试 ===')
severities = [FaultSeverity.LOW, FaultSeverity.MEDIUM, FaultSeverity.HIGH, FaultSeverity.CRITICAL]
for sev in severities:
    print(f'  {sev.value}: priority = {sev.priority}')

print()
highest = max(severities, key=lambda s: s.priority)
print(f'最高级别: {highest.value} (priority={highest.priority})')
print()

print('所有测试通过!' if all_passed else '有测试失败!')
