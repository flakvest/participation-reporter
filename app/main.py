import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password
from app.config import settings
from app.database import Base, engine, get_db
from app.models import User
from app.routes.auth import router as auth_router
from app.routes.reports import router as reports_router
from app.templates import templates

app = FastAPI(title="MARS Platoon Participation Reporter")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router)
app.include_router(reports_router)


@app.on_event("startup")
def startup():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    existing = db.query(User).filter(User.callsign == settings.admin_username.upper()).first()
    if not existing:
        admin = User(
            callsign=settings.admin_username.upper(),
            password_hash=hash_password(settings.admin_password),
            platoon="1PLT",
            role="admin",
        )
        db.add(admin)
        db.commit()


@app.get("/")
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)
