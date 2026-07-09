import io
import base64
from datetime import timedelta

import qrcode
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_user,
    decode_token,
    generate_totp_secret,
    get_current_user,
    get_totp_uri,
    get_user_by_callsign,
    require_user,
    verify_password,
    verify_totp,
)
from app.config import settings
from app.database import get_db
from app.models import User
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

    if user.totp_enabled:
        preauth_token = create_access_token(
            {"sub": user.callsign, "scope": "totp_required"},
            expires_delta=timedelta(minutes=5),
        )
        resp = RedirectResponse(url="/login/2fa", status_code=302)
        resp.set_cookie(key="preauth_token", value=preauth_token, httponly=True, max_age=300)
        return resp

    token = create_access_token({"sub": user.callsign, "role": user.role, "platoon": user.platoon})
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.access_token_expire_minutes * 60)
    return resp


@router.get("/login/2fa")
def login_2fa_form(request: Request, db: Session = Depends(get_db)):
    preauth = request.cookies.get("preauth_token")
    if not preauth:
        return RedirectResponse(url="/login", status_code=302)
    payload = decode_token(preauth)
    if not payload or payload.get("scope") != "totp_required":
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("login_2fa.html", {"request": request, "callsign": payload.get("sub")})


@router.post("/login/2fa")
def login_2fa(request: Request, response: Response, code: str = Form(...), db: Session = Depends(get_db)):
    preauth = request.cookies.get("preauth_token")
    if not preauth:
        return RedirectResponse(url="/login", status_code=302)
    payload = decode_token(preauth)
    if not payload or payload.get("scope") != "totp_required":
        return RedirectResponse(url="/login", status_code=302)

    callsign = payload.get("sub")
    user = get_user_by_callsign(db, callsign)
    if not user or not user.totp_enabled or not user.totp_secret:
        return RedirectResponse(url="/login", status_code=302)

    if not verify_totp(user.totp_secret, code):
        return templates.TemplateResponse(
            "login_2fa.html",
            {"request": request, "callsign": callsign, "error": "Invalid code. Try again."},
        )

    token = create_access_token({"sub": user.callsign, "role": user.role, "platoon": user.platoon})
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.access_token_expire_minutes * 60)
    resp.delete_cookie("preauth_token")
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
    resp.delete_cookie("preauth_token")
    return resp


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_user)):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
    })


@router.post("/settings/2fa/enable")
def enable_2fa(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_user)):
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()

    uri = get_totp_uri(secret, current_user.callsign)
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
        "qr_data": qr_b64,
        "totp_secret": secret,
        "pending_enable": True,
    })


@router.post("/settings/2fa/verify")
def verify_2fa(request: Request, code: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(require_user)):
    if not current_user.totp_secret:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": current_user,
            "error_2fa": "No TOTP secret found. Enable 2FA first.",
        })

    if not verify_totp(current_user.totp_secret, code):
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": current_user,
            "error_2fa": "Invalid code. Scan the QR code again and enter the current code.",
        })

    current_user.totp_enabled = True
    db.commit()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
        "success_2fa": "Two-factor authentication is now enabled.",
    })


@router.post("/settings/2fa/disable")
def disable_2fa(request: Request, code: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(require_user)):
    if not current_user.totp_enabled or not current_user.totp_secret:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": current_user,
            "error_2fa": "2FA is not enabled.",
        })

    if not verify_totp(current_user.totp_secret, code):
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": current_user,
            "error_2fa": "Invalid code. 2FA was not disabled.",
        })

    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.commit()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
        "success_2fa": "Two-factor authentication has been disabled.",
    })
