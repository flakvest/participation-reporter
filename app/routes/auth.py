from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import create_access_token, create_user, get_current_user, get_user_by_callsign, verify_password
from app.config import settings
from app.database import get_db
from app.schemas import PLATOONS
from app.templates import templates

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_form(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, response: Response, callsign: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = get_user_by_callsign(db, callsign.strip().upper())
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid callsign or password"})
    token = create_access_token({"sub": user.callsign, "role": user.role, "platoon": user.platoon})
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.access_token_expire_minutes * 60)
    return resp


@router.get("/register")
def register_form(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "platoons": sorted(PLATOONS)})


@router.post("/register")
def register(
    request: Request,
    response: Response,
    callsign: str = Form(...),
    password: str = Form(...),
    platoon: str = Form(...),
    db: Session = Depends(get_db),
):
    callsign_clean = callsign.strip().upper()
    platoon_clean = platoon.strip().upper()

    if platoon_clean not in PLATOONS:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Invalid platoon", "platoons": sorted(PLATOONS)})
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Password must be at least 6 characters", "platoons": sorted(PLATOONS)})

    existing = get_user_by_callsign(db, callsign_clean)
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Callsign already registered", "platoons": sorted(PLATOONS)})

    role = "platoon_leader" if callsign_clean == settings.admin_username.upper() else "operator"
    create_user(db, callsign_clean, password, platoon_clean, role)
    token = create_access_token({"sub": callsign_clean, "role": role, "platoon": platoon_clean})
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.access_token_expire_minutes * 60)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
