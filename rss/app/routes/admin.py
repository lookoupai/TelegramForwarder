from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.models import ForwardRule, Keyword, get_session
from rss.app.routes.auth import get_current_user
from services.admin_management_service import (
    ChatOut,
    PushConfigCreate,
    PushConfigOut,
    PushConfigUpdate,
    PushSettingsOut,
    PushSettingsUpdate,
    RuleCreate,
    SyncRuleCreate,
    SyncRuleOut,
    TemplateSettingsOut,
    TemplateSettingsUpdate,
    UFBSettingsOut,
    UFBSettingsUpdate,
    add_push_config,
    add_sync_rule,
    create_rule,
    delete_push_config,
    delete_rule,
    delete_sync_rule,
    get_push_settings,
    get_template_settings,
    get_ufb_settings,
    list_chats,
    list_sync_rules,
    update_push_config,
    update_push_settings,
    update_template_settings,
    update_ufb_settings,
)
from services.rule_extras_service import (
    AISettingsOut,
    AISettingsUpdate,
    KeywordCreate,
    KeywordOut,
    MediaExtensionCreate,
    MediaExtensionOut,
    MediaSettingsOut,
    MediaSettingsUpdate,
    ReplaceRuleCreate,
    ReplaceRuleOut,
    add_media_extension,
    create_keyword,
    create_replace_rule,
    delete_keyword,
    delete_media_extension,
    delete_replace_rule,
    get_ai_settings,
    get_media_settings,
    list_keywords,
    list_media_extensions,
    list_replace_rules,
    update_ai_settings,
    update_media_settings,
)
from services.rule_bulk_service import (
    BulkResult,
    CopyToRule,
    KeywordAdvancedSettingsOut,
    KeywordAdvancedSettingsUpdate,
    KeywordBulkCreate,
    ReplaceBulkCreate,
    bulk_add_keywords,
    bulk_add_replace_rules,
    clear_keywords,
    clear_replace_rules,
    copy_keywords,
    copy_replace_rules,
    export_keywords,
    export_replace_rules,
    get_keyword_advanced_settings,
    update_keyword_advanced_settings,
)
from services.admin_action_service import enqueue_action
from services.rule_copy_service import RuleCopyRequest, RuleCopyResult, copy_rule_to
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


def _enqueue_ufb_sync_if_needed(session, rule_id: int) -> None:
    try:
        rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
        if not rule:
            return
        if bool(getattr(rule, "is_ufb", False)) and getattr(rule, "ufb_domain", None):
            enqueue_action(session, action="ufb_sync", rule_id=rule_id)
    except Exception:
        return


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


@router.get("/api/chats", response_model=List[ChatOut])
async def fetch_chats(user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_chats(session)
    finally:
        session.close()


@router.post("/api/chats/update-now")
async def trigger_update_chats_now(user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        action_id = enqueue_action(session, action="update_chats_now", rule_id=None)
        return {"ok": True, "action_id": action_id}
    finally:
        session.close()


@router.post("/api/rules", response_model=RuleDetail)
async def create_new_rule(payload: RuleCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            rule = create_rule(session, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        detail = get_rule_detail(session, rule.id)
        if not detail:
            raise HTTPException(status_code=500, detail="规则创建成功但读取失败")
        return detail
    finally:
        session.close()


@router.delete("/api/rules/{rule_id}")
async def remove_rule(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        deleted = delete_rule(session, rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="规则不存在")
        return {"ok": True}
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/templates", response_model=TemplateSettingsOut)
async def fetch_templates(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_template_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/templates", response_model=TemplateSettingsOut)
async def save_templates(rule_id: int, payload: TemplateSettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_template_settings(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/sync-rules", response_model=List[SyncRuleOut])
async def fetch_sync_rules(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_sync_rules(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/sync-rules", response_model=List[SyncRuleOut])
async def add_sync_target(rule_id: int, payload: SyncRuleCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return add_sync_rule(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.delete("/api/rules/{rule_id}/sync-rules/{rule_sync_id}", response_model=List[SyncRuleOut])
async def remove_sync_target(rule_id: int, rule_sync_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return delete_sync_rule(session, rule_id, rule_sync_id)
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/push-settings", response_model=PushSettingsOut)
async def fetch_push_settings(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_push_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/push-settings", response_model=PushSettingsOut)
async def save_push_settings(rule_id: int, payload: PushSettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_push_settings(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/push-configs", response_model=PushSettingsOut)
async def add_rule_push_config(rule_id: int, payload: PushConfigCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return add_push_config(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/push-configs/{push_config_id}", response_model=PushConfigOut)
async def save_push_config(push_config_id: int, payload: PushConfigUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_push_config(session, push_config_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.delete("/api/rules/{rule_id}/push-configs/{push_config_id}", response_model=PushSettingsOut)
async def remove_push_config(rule_id: int, push_config_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return delete_push_config(session, rule_id, push_config_id)
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/ufb-settings", response_model=UFBSettingsOut)
async def fetch_ufb_settings(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_ufb_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/ufb-settings", response_model=UFBSettingsOut)
async def save_ufb_settings(rule_id: int, payload: UFBSettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            result = update_ufb_settings(session, rule_id, payload)
            _enqueue_ufb_sync_if_needed(session, rule_id)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/keywords", response_model=List[KeywordOut])
async def fetch_rule_keywords(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_keywords(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/keywords", response_model=KeywordOut)
async def add_rule_keyword(rule_id: int, payload: KeywordCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            created = create_keyword(session, rule_id, payload)
            _enqueue_ufb_sync_if_needed(session, rule_id)
            return created
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.delete("/api/keywords/{keyword_id}")
async def remove_keyword(keyword_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        existing = session.query(Keyword).filter(Keyword.id == keyword_id).first()
        rule_id = int(existing.rule_id) if existing else None
        deleted = delete_keyword(session, keyword_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="关键字不存在")
        if rule_id:
            _enqueue_ufb_sync_if_needed(session, rule_id)
        return {"ok": True}
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/replace-rules", response_model=List[ReplaceRuleOut])
async def fetch_rule_replace_rules(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_replace_rules(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/replace-rules", response_model=ReplaceRuleOut)
async def add_rule_replace_rule(rule_id: int, payload: ReplaceRuleCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return create_replace_rule(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.delete("/api/replace-rules/{replace_rule_id}")
async def remove_replace_rule(replace_rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        deleted = delete_replace_rule(session, replace_rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="替换规则不存在")
        return {"ok": True}
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/media-settings", response_model=MediaSettingsOut)
async def fetch_media_settings(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_media_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/media-settings", response_model=MediaSettingsOut)
async def save_media_settings(rule_id: int, payload: MediaSettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_media_settings(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/media-extensions", response_model=List[MediaExtensionOut])
async def fetch_media_extensions(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return list_media_extensions(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/media-extensions", response_model=List[MediaExtensionOut])
async def add_rule_media_extension(rule_id: int, payload: MediaExtensionCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return add_media_extension(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.delete("/api/rules/{rule_id}/media-extensions/{extension_id}", response_model=List[MediaExtensionOut])
async def remove_rule_media_extension(rule_id: int, extension_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return delete_media_extension(session, rule_id, extension_id)
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/ai-settings", response_model=AISettingsOut)
async def fetch_ai_settings(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_ai_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/ai-settings", response_model=AISettingsOut)
async def save_ai_settings(rule_id: int, payload: AISettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_ai_settings(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/keywords/export", response_model=List[str])
async def export_rule_keywords(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return export_keywords(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/keywords/bulk", response_model=BulkResult)
async def bulk_add_rule_keywords(rule_id: int, payload: KeywordBulkCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            result = bulk_add_keywords(session, rule_id, payload)
            _enqueue_ufb_sync_if_needed(session, rule_id)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/keywords/clear")
async def clear_rule_keywords(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        deleted = clear_keywords(session, rule_id)
        _enqueue_ufb_sync_if_needed(session, rule_id)
        return {"ok": True, "deleted": deleted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/keywords/copy", response_model=BulkResult)
async def copy_rule_keywords(rule_id: int, payload: CopyToRule, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            result = copy_keywords(session, rule_id, payload.target_rule_id)
            _enqueue_ufb_sync_if_needed(session, payload.target_rule_id)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/replace-rules/export", response_model=List[str])
async def export_rule_replace_rules(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        return export_replace_rules(session, rule_id)
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/replace-rules/bulk", response_model=BulkResult)
async def bulk_add_rule_replace_rules(rule_id: int, payload: ReplaceBulkCreate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return bulk_add_replace_rules(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/replace-rules/clear")
async def clear_rule_replace_rules(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        deleted = clear_replace_rules(session, rule_id)
        return {"ok": True, "deleted": deleted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/replace-rules/copy", response_model=BulkResult)
async def copy_rule_replace_rules(rule_id: int, payload: CopyToRule, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return copy_replace_rules(session, rule_id, payload.target_rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/api/rules/{rule_id}/keywords/advanced", response_model=KeywordAdvancedSettingsOut)
async def fetch_keyword_advanced(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return get_keyword_advanced_settings(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.put("/api/rules/{rule_id}/keywords/advanced", response_model=KeywordAdvancedSettingsOut)
async def save_keyword_advanced(rule_id: int, payload: KeywordAdvancedSettingsUpdate, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            return update_keyword_advanced_settings(session, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/ai-summary-now")
async def trigger_ai_summary_now(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        action_id = enqueue_action(session, action="summary_now", rule_id=rule_id)
        return {"ok": True, "action_id": action_id}
    finally:
        session.close()


@router.post("/api/ai-summary/execute-all")
async def trigger_ai_summary_all(user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        action_id = enqueue_action(session, action="summary_all_now", rule_id=None)
        return {"ok": True, "action_id": action_id}
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/ufb-sync-now")
async def trigger_ufb_sync_now(rule_id: int, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        action_id = enqueue_action(session, action="ufb_sync", rule_id=rule_id)
        return {"ok": True, "action_id": action_id}
    finally:
        session.close()


@router.post("/api/rules/{rule_id}/copy-to", response_model=RuleCopyResult)
async def copy_rule_settings_to(rule_id: int, payload: RuleCopyRequest, user=Depends(get_current_user)):
    _require_user(user)
    session = get_session()
    try:
        try:
            result = copy_rule_to(session, rule_id, payload)
            _enqueue_ufb_sync_if_needed(session, payload.target_rule_id)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()
