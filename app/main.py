from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import members, resources, bookings, approvals, payments, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="共享办公空间智能调度与运营管理系统API",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(members.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/", tags=["系统"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "healthy"}
