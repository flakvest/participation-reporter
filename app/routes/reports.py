import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_user
from app.database import get_db
from app.models import Report, User
from app.rri_parser import FIELD_DEFS_PLATOON, MONTHS, parse_text
from app.templates import templates

router = APIRouter(tags=["reports"])


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    if user.role == "admin":
        users = db.query(User).all()
    elif user.role == "platoon_leader":
        users = db.query(User).filter(User.platoon == user.platoon).all()
    else:
        users = [user]

    report_list = []
    for u in users:
        latest = db.query(Report).filter(Report.callsign == u.callsign).order_by(Report.created_at.desc()).first()
        report_list.append({
            "callsign": u.callsign,
            "platoon": u.platoon,
            "last_report": latest.month if latest else None,
            "last_report_date": latest.created_at if latest else None,
            "has_submitted": latest is not None,
        })

    if user.role != "admin":
        report_list = [r for r in report_list if r["platoon"] == user.platoon]

    report_list.sort(key=lambda r: r["callsign"])
    total_members = len(report_list)
    submitted_count = sum(1 for r in report_list if r["has_submitted"])
    missing_count = total_members - submitted_count
    submission_pct = round(submitted_count / total_members * 100) if total_members > 0 else 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "report_list": report_list,
        "total_members": total_members,
        "submitted_count": submitted_count,
        "missing_count": missing_count,
        "submission_pct": submission_pct,
        "months": sorted(MONTHS),
        "platoons": ["1PLT", "2PLT"],
    })


@router.get("/submit")
def submit_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("submit.html", {
        "request": request,
        "user": user,
    })


@router.post("/submit")
def submit_paste(
    request: Request,
    strip_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    results = parse_text(strip_text)
    successes = []
    errors = []

    for parsed_report, parse_errors in results:
        if parsed_report is None:
            errors.extend(parse_errors)
            continue
        if parse_errors:
            errors.extend(parse_errors)
            continue

        existing = db.query(Report).filter(
            Report.platoon == parsed_report.platoon,
            Report.callsign == parsed_report.callsign,
            Report.month == parsed_report.month,
        ).first()

        report = Report(
            platoon=parsed_report.platoon,
            callsign=parsed_report.callsign,
            month=parsed_report.month,
            equipment_ok=parsed_report.equipment_ok,
            skills_ok=parsed_report.skills_ok,
            total_hf_hours=parsed_report.total_hf_hours,
            j0g_hours=parsed_report.j0g_hours,
            gst_hours=parsed_report.gst_hours,
            other_hf_hours=parsed_report.other_hf_hours,
            total_mars_hours=parsed_report.total_mars_hours,
            notes=parsed_report.notes,
            submission_source="paste",
            duplicate_flag=existing is not None,
            submitted_by=current_user.callsign,
        )
        db.add(report)
        successes.append(parsed_report)

    db.commit()

    return templates.TemplateResponse("submit.html", {
        "request": request,
        "user": current_user,
        "successes": successes,
        "errors": errors,
    })


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    results = parse_text(text)
    successes = []
    errors = []

    for parsed_report, parse_errors in results:
        if parsed_report is None:
            errors.extend(parse_errors)
            continue
        if parse_errors:
            errors.extend(parse_errors)
            continue

        existing = db.query(Report).filter(
            Report.platoon == parsed_report.platoon,
            Report.callsign == parsed_report.callsign,
            Report.month == parsed_report.month,
        ).first()

        report = Report(
            platoon=parsed_report.platoon,
            callsign=parsed_report.callsign,
            month=parsed_report.month,
            equipment_ok=parsed_report.equipment_ok,
            skills_ok=parsed_report.skills_ok,
            total_hf_hours=parsed_report.total_hf_hours,
            j0g_hours=parsed_report.j0g_hours,
            gst_hours=parsed_report.gst_hours,
            other_hf_hours=parsed_report.other_hf_hours,
            total_mars_hours=parsed_report.total_mars_hours,
            notes=parsed_report.notes,
            submission_source="file_upload",
            duplicate_flag=existing is not None,
            submitted_by=current_user.callsign,
        )
        db.add(report)
        successes.append(parsed_report)

    db.commit()

    return templates.TemplateResponse("submit.html", {
        "request": request,
        "user": current_user,
        "successes": successes,
        "errors": errors,
        "filename": file.filename,
    })


@router.get("/reports")
def view_reports(
    request: Request,
    platoon: str = "",
    month: str = "",
    callsign: str = "",
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    query = db.query(Report)

    if user.role == "operator":
        query = query.filter(Report.callsign == user.callsign)
    elif user.role == "platoon_leader":
        query = query.filter(Report.platoon == user.platoon)
        if platoon:
            query = query.filter(Report.platoon == platoon.upper())
    elif user.role == "admin":
        if platoon:
            query = query.filter(Report.platoon == platoon.upper())

    if month:
        query = query.filter(Report.month == month.upper())
    if callsign:
        query = query.filter(Report.callsign == callsign.upper())

    reports = query.order_by(Report.created_at.desc()).all()

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "reports": reports,
        "filter_platoon": platoon,
        "filter_month": month,
        "filter_callsign": callsign,
        "months": sorted(MONTHS),
        "platoons": ["1PLT", "2PLT"],
    })


@router.get("/reports/export")
def export_csv(
    platoon: str = "",
    month: str = "",
    callsign: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    query = db.query(Report)

    if current_user.role == "operator":
        query = query.filter(Report.callsign == current_user.callsign)
    elif current_user.role == "platoon_leader":
        query = query.filter(Report.platoon == current_user.platoon)
        if platoon:
            query = query.filter(Report.platoon == platoon.upper())
    elif current_user.role == "admin":
        if platoon:
            query = query.filter(Report.platoon == platoon.upper())

    if month:
        query = query.filter(Report.month == month.upper())
    if callsign:
        query = query.filter(Report.callsign == callsign.upper())

    reports = query.order_by(Report.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    field_names = [f[0] for f in FIELD_DEFS_PLATOON]
    writer.writerow(["Platoon", "Callsign", *field_names, "Submission Source", "Duplicate", "Submitted By", "Submitted At"])

    for r in reports:
        writer.writerow([
            r.platoon, r.callsign,
            r.month, r.equipment_ok, r.skills_ok,
            r.total_hf_hours, r.j0g_hours, r.gst_hours,
            r.other_hf_hours, r.total_mars_hours,
            r.notes,
            r.submission_source, "YES" if r.duplicate_flag else "NO",
            r.submitted_by, r.created_at.isoformat(),
        ])

    output.seek(0)
    filename = f"mars_reports_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
