from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.models import get_session
from rss.app.routes.auth import get_current_user
from services.rule_service import (
    ADMIN_SETTING_FIELDS,
    RuleDetail,
    RuleSummary,
    RuleUpdate,
    get_rule_detail,
    get_setting_schema,
    list_rules,
    update_rule_settings,
)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="rss/app/templates")


def _require_user(user):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    schema = get_setting_schema()
    ordered_fields = [
        (field, schema[field]) for field in ADMIN_SETTING_FIELDS if field in schema
    ]
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "form_fields": ordered_fields,
        },
    )


@router.get("/view/rules", response_class=HTMLResponse)
async def view_rules(request: Request, user=Depends(get_current_user)):
    if not user:
        return HTMLResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content="",
        )

    session = get_session()
    try:
        rules = [rule.dict() for rule in list_rules(session)]
    finally:
        session.close()

    return templates.TemplateResponse(
        "admin/rules_table.html",
        {"request": request, "rules": rules},
    )


@router.get("/api/schema")
async def fetch_schema(user=Depends(get_current_user)):
    _require_user(user)
    return get_setting_schema()


@router.get("/api/rules", response_model=List[RuleSummary])
async def fetch_rules(user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_rules(session)
    finally:
        session.close()


@router.get("/api/rules/{rule_id}", response_model=RuleDetail)
async def fetch_rule(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        detail = get_rule_detail(session, rule_id)
        if not detail:
            raise HTTPException(status_code=404, detail="规则不存在")
        return detail
    finally:
        session.close()


@router.put("/api/rules/{rule_id}", response_model=RuleDetail)
async def update_rule(rule_id: int, payload: RuleUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        updated = update_rule_settings(session, rule_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="规则不存在")
        return updated
    finally:
        session.close()
