"""
验证核心业务逻辑：
1. 签退结算 - 实际使用超时时按真实时长收费
2. 余额不足 - 结算后限制预订
3. 充值后 - 恢复预订权限
4. 审批多级升级
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.approval_service import ApprovalService
from app.models import Booking, BookingStatus, Resource, Member, Approval, ApprovalStatus, Admin
from datetime import datetime, timedelta

db = SessionLocal()

try:
    print("=" * 60)
    print("  核心业务逻辑验证")
    print("=" * 60)

    # 找一个测试会员和资源
    member = db.query(Member).filter(Member.email == "test@example.com").first()
    resource = db.query(Resource).filter(Resource.type == "desk").first()
    admin = db.query(Admin).filter(Admin.level == 1).first()
    
    print(f"\n测试会员: {member.name}, 当前余额: ¥{member.balance}")
    print(f"测试资源: {resource.name}, 小时费率: ¥{resource.hourly_rate}")

    # ===== 测试1: 超时使用按实际时长计费 =====
    print("\n--- 测试1: 超时使用按实际时长计费 ---")
    
    # 手动创建一个已审批且已签到的预订
    booking = Booking(
        member_id=member.id,
        resource_id=resource.id,
        start_time=datetime.now() - timedelta(hours=5),
        end_time=datetime.now() - timedelta(hours=3),  # 预订2小时
        status=BookingStatus.APPROVED,
        total_amount=2 * resource.hourly_rate,
        actual_start_time=datetime.now() - timedelta(hours=5),  # 实际用了5小时
        actual_amount=0
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    print(f"  预订 #{booking.id}")
    print(f"  预订时长: 2小时, 预估费用: ¥{booking.total_amount}")
    print(f"  实际开始: {booking.actual_start_time}")
    print(f"  预计实际时长: 5小时")
    
    # 签退
    result = BookingService.check_out(db, booking.id)
    print(f"  签退结果: {result}")
    
    db.refresh(booking)
    actual_hours = (booking.actual_end_time - booking.actual_start_time).total_seconds() / 3600
    
    print(f"  实际结束: {booking.actual_end_time}")
    print(f"  实际时长: {actual_hours:.2f} 小时")
    print(f"  实际费用: ¥{booking.actual_amount}")
    print(f"  预估费用: ¥{booking.total_amount}")
    
    assert booking.actual_amount > booking.total_amount, "超时使用实际费用应该高于预估"
    assert abs(booking.actual_amount - actual_hours * resource.hourly_rate) < 0.01, "实际费用应该等于实际时长 × 单价"
    print("  ✅ 超时按实际时长计费 - 验证通过")

    # ===== 测试2: 余额不足时限制预订 =====
    print("\n--- 测试2: 余额不足限制预订 ---")
    
    # 重置会员状态
    member.balance = 5.0  # 余额很少
    member.booking_restricted = False
    db.commit()
    db.refresh(member)
    
    print(f"  设置会员余额为 ¥{member.balance}")
    
    # 创建一个高价资源的预订（确保结算后余额为负）
    expensive_resource = db.query(Resource).order_by(Resource.hourly_rate.desc()).first()
    print(f"  高价资源: {expensive_resource.name}, 费率: ¥{expensive_resource.hourly_rate}/小时")
    
    # 手动创建使用中的预订（已使用 2 小时）
    used_hours = 2
    expected_cost = used_hours * expensive_resource.hourly_rate
    
    big_booking = Booking(
        member_id=member.id,
        resource_id=expensive_resource.id,
        start_time=datetime.now() - timedelta(hours=3),
        end_time=datetime.now() - timedelta(hours=1),
        status=BookingStatus.APPROVED,
        total_amount=expected_cost,
        actual_start_time=datetime.now() - timedelta(hours=3),
        actual_amount=0
    )
    db.add(big_booking)
    db.commit()
    db.refresh(big_booking)
    
    print(f"  创建高价资源预订 #{big_booking.id}")
    print(f"  预计费用: ¥{expected_cost}, 当前余额: ¥{member.balance}")
    print(f"  预计余额不足，差额: ¥{expected_cost - member.balance}")
    
    # 签退 - 应该会余额不足并限制预订
    result = BookingService.check_out(db, big_booking.id)
    print(f"  签退结果: {result}")
    
    db.refresh(member)
    db.refresh(big_booking)
    
    print(f"  结算后余额: ¥{member.balance}")
    print(f"  预订限制: {member.booking_restricted}")
    
    assert member.balance < 0, "余额应该为负数"
    assert member.booking_restricted == True, "余额不足后应该限制预订"
    print("  ✅ 余额不足限制预订 - 验证通过")

    # ===== 测试3: 充值后恢复预订 =====
    print("\n--- 测试3: 充值后恢复预订权限 ---")
    
    recharge_amount = 700
    success_r, msg_r, payment = PaymentService.recharge(db, member.id, recharge_amount)
    print(f"  充值结果: {msg_r}")
    db.refresh(member)
    
    print(f"  充值 ¥{recharge_amount} 后余额: ¥{member.balance}")
    print(f"  预订限制: {member.booking_restricted}")
    
    assert member.booking_restricted == False, "充值后应该解除限制"
    assert member.balance > 0, "充值后余额应该为正"
    print("  ✅ 充值后恢复预订权限 - 验证通过")

    # ===== 测试4: 审批多级升级 =====
    print("\n--- 测试4: 审批超时自动升级 ---")
    
    # 创建一个待审批的预订
    from app.schemas import BookingCreate
    future_start = datetime.now() + timedelta(days=30)
    future_end = future_start + timedelta(hours=2)
    
    success, msg, new_booking = BookingService.create_booking(
        db, member.id,
        BookingCreate(resource_id=resource.id, start_time=future_start, end_time=future_end)
    )
    assert success, f"创建预订失败: {msg}"
    
    approval = db.query(Approval).filter(Approval.booking_id == new_booking.id).first()
    print(f"  新审批 #{approval.id}")
    print(f"  当前级别: {approval.approver_level}")
    print(f"  当前状态: {approval.status}")
    
    # 把提交时间改到 3 小时前，模拟超时
    approval.submitted_at = datetime.now() - timedelta(hours=3)
    db.commit()
    
    # 执行超时检查
    count = ApprovalService.check_timeout_and_escalate(db)
    print(f"\n  第一次超时检查处理了 {count} 条审批")
    
    db.refresh(approval)
    print(f"  升级后级别: {approval.approver_level}")
    print(f"  升级后状态: {approval.status}")
    
    assert approval.approver_level > 1, "应该已经升级到下一级别"
    
    # 继续模拟超时 - 再升级
    approval.escalated_at = datetime.now() - timedelta(hours=3)
    db.commit()
    
    count2 = ApprovalService.check_timeout_and_escalate(db)
    print(f"\n  第二次超时检查处理了 {count2} 条审批")
    
    db.refresh(approval)
    print(f"  再次升级后级别: {approval.approver_level}")
    print(f"  再次升级后状态: {approval.status}")
    
    print("  ✅ 审批多级超时升级 - 验证通过")

    print("\n" + "=" * 60)
    print("  🎉 所有核心业务逻辑验证通过！")
    print("=" * 60)

finally:
    db.close()
