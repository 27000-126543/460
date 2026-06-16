from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.approval_service import ApprovalService
from app.services.work_order_service import WorkOrderService
from datetime import datetime

scheduler = BackgroundScheduler()


def check_approval_timeout():
    db = SessionLocal()
    try:
        count = ApprovalService.check_timeout_and_escalate(db)
        if count > 0:
            print(f"[{datetime.now()}] 审批超时检查完成，处理了 {count} 条超时审批")
    except Exception as e:
        print(f"[{datetime.now()}] 审批超时检查出错: {e}")
    finally:
        db.close()


def check_work_order_timeout():
    db = SessionLocal()
    try:
        count = WorkOrderService.check_timeout_and_escalate(db)
        if count > 0:
            print(f"[{datetime.now()}] 工单超时检查完成，处理了 {count} 条超时工单")
    except Exception as e:
        print(f"[{datetime.now()}] 工单超时检查出错: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        check_approval_timeout,
        'interval',
        minutes=5,
        id='check_approval_timeout',
        replace_existing=True
    )
    scheduler.add_job(
        check_work_order_timeout,
        'interval',
        minutes=5,
        id='check_work_order_timeout',
        replace_existing=True
    )
    scheduler.start()
    print("后台调度任务已启动")


def stop_scheduler():
    scheduler.shutdown()
    print("后台调度任务已停止")
