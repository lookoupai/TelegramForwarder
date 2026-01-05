from models.models import get_session
from telethon import Button
from utils.constants import RSS_ENABLED, UFB_ENABLED
from services.rule_settings import (
    RULE_SETTINGS,
    AI_SETTINGS,
    MEDIA_SETTINGS,
    OTHER_SETTINGS,
    PUSH_SETTINGS,
    AI_MODELS,
)


async def create_settings_text(rule):
    """创建设置信息文本"""
    text = (
        "📋 管理转发规则\n\n"
        f"规则ID: `{rule.id}`\n"
        f"{rule.source_chat.name} --> {rule.target_chat.name}"
    )
    return text


async def create_buttons(rule):
    """创建规则设置按钮"""
    buttons = []

    session = get_session()
    try:
        target_chat = rule.target_chat
        current_add_id = target_chat.current_add_id
        source_chat = rule.source_chat

        is_current = current_add_id == source_chat.telegram_chat_id
        buttons.append(
            [
                Button.inline(
                    f"{'✅ ' if is_current else ''}应用当前规则",
                    f"toggle_current:{rule.id}",
                )
            ]
        )

        buttons.append(
            [
                Button.inline(
                    f"是否启用规则: {RULE_SETTINGS['enable_rule']['values'][rule.enable_rule]}",
                    f"toggle_enable_rule:{rule.id}",
                )
            ]
        )

        buttons.append(
            [
                Button.inline(
                    f"当前关键字添加模式: {RULE_SETTINGS['add_mode']['values'][rule.add_mode]}",
                    f"toggle_add_mode:{rule.id}",
                )
            ]
        )

        buttons.append(
            [
                Button.inline(
                    f"过滤关键字时是否附带发送者名称和ID: {RULE_SETTINGS['is_filter_user_info']['values'][rule.is_filter_user_info]}",
                    f"toggle_filter_user_info:{rule.id}",
                )
            ]
        )

        if RSS_ENABLED == "false":
            buttons.append(
                [
                    Button.inline(
                        f"⚙️ 处理模式: {RULE_SETTINGS['handle_mode']['values'][rule.handle_mode]}",
                        f"toggle_handle_mode:{rule.id}",
                    )
                ]
            )
        else:
            buttons.append(
                [
                    Button.inline(
                        f"⚙️ 处理模式: {RULE_SETTINGS['handle_mode']['values'][rule.handle_mode]}",
                        f"toggle_handle_mode:{rule.id}",
                    ),
                    Button.inline(
                        f"⚠️ 只转发到RSS: {RULE_SETTINGS['only_rss']['values'][rule.only_rss]}",
                        f"toggle_only_rss:{rule.id}",
                    ),
                ]
            )

        buttons.append(
            [
                Button.inline(
                    f"📥 过滤模式: {RULE_SETTINGS['forward_mode']['values'][rule.forward_mode]}",
                    f"toggle_forward_mode:{rule.id}",
                ),
                Button.inline(
                    f"🤖 转发方式: {RULE_SETTINGS['use_bot']['values'][rule.use_bot]}",
                    f"toggle_bot:{rule.id}",
                ),
            ]
        )

        if rule.use_bot:
            buttons.append(
                [
                    Button.inline(
                        f"🔄 替换模式: {RULE_SETTINGS['is_replace']['values'][rule.is_replace]}",
                        f"toggle_replace:{rule.id}",
                    ),
                    Button.inline(
                        f"📝 消息格式: {RULE_SETTINGS['message_mode']['values'][rule.message_mode]}",
                        f"toggle_message_mode:{rule.id}",
                    ),
                ]
            )

            buttons.append(
                [
                    Button.inline(
                        f"👁 预览模式: {RULE_SETTINGS['is_preview']['values'][rule.is_preview]}",
                        f"toggle_preview:{rule.id}",
                    ),
                    Button.inline(
                        f"🔗 原始链接: {RULE_SETTINGS['is_original_link']['values'][rule.is_original_link]}",
                        f"toggle_original_link:{rule.id}",
                    ),
                ]
            )

            buttons.append(
                [
                    Button.inline(
                        f"👤 原始发送者: {RULE_SETTINGS['is_original_sender']['values'][rule.is_original_sender]}",
                        f"toggle_original_sender:{rule.id}",
                    ),
                    Button.inline(
                        f"⏰ 发送时间: {RULE_SETTINGS['is_original_time']['values'][rule.is_original_time]}",
                        f"toggle_original_time:{rule.id}",
                    ),
                ]
            )

            buttons.append(
                [
                    Button.inline(
                        f"🗑 删除原消息: {RULE_SETTINGS['is_delete_original']['values'][rule.is_delete_original]}",
                        f"toggle_delete_original:{rule.id}",
                    ),
                    Button.inline(
                        f"💬 评论区按钮: {RULE_SETTINGS['enable_comment_button']['values'][rule.enable_comment_button]}",
                        f"toggle_enable_comment_button:{rule.id}",
                    ),
                ]
            )

            buttons.append(
                [
                    Button.inline(
                        f"⏱️ 延迟处理: {RULE_SETTINGS['enable_delay']['values'][rule.enable_delay]}",
                        f"toggle_enable_delay:{rule.id}",
                    ),
                    Button.inline(
                        f"⌛ 延迟秒数: {rule.delay_seconds or 5}秒",
                        f"set_delay_time:{rule.id}",
                    ),
                ]
            )

            buttons.append(
                [
                    Button.inline(
                        f"🔄 同步规则: {RULE_SETTINGS['enable_sync']['values'][rule.enable_sync]}",
                        f"toggle_enable_sync:{rule.id}",
                    ),
                    Button.inline("📡 同步设置", f"set_sync_rule:{rule.id}"),
                ]
            )

            if UFB_ENABLED == "true":
                buttons.append(
                    [
                        Button.inline(
                            f"☁️ UFB同步: {RULE_SETTINGS['is_ufb']['values'][rule.is_ufb]}",
                            f"toggle_ufb:{rule.id}",
                        )
                    ]
                )

            buttons.append(
                [
                    Button.inline("🤖 AI设置", f"ai_settings:{rule.id}"),
                    Button.inline("🎬 媒体设置", f"media_settings:{rule.id}"),
                    Button.inline("➕ 其他设置", f"other_settings:{rule.id}"),
                ]
            )

            buttons.append(
                [
                    Button.inline("🔔 推送设置", f"push_settings:{rule.id}"),
                ]
            )

            buttons.append(
                [
                    Button.inline("👈 返回", "settings"),
                    Button.inline("❌ 关闭", "close_settings"),
                ]
            )
    finally:
        session.close()

    return buttons
