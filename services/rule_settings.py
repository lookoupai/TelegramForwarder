from utils.settings import load_ai_models
from enums.enums import ForwardMode, MessageMode, PreviewMode, AddMode, HandleMode

AI_MODELS = load_ai_models()

# 规则配置字段定义
RULE_SETTINGS = {
    'enable_rule': {
        'display_name': '是否启用规则',
        'values': {
            True: '是',
            False: '否'
        },
        'toggle_action': 'toggle_enable_rule',
        'toggle_func': lambda current: not current
    },
    'add_mode': {
        'display_name': '当前关键字添加模式',
        'values': {
            AddMode.WHITELIST: '白名单',
            AddMode.BLACKLIST: '黑名单'
        },
        'toggle_action': 'toggle_add_mode',
        'toggle_func': lambda current: AddMode.BLACKLIST if current == AddMode.WHITELIST else AddMode.WHITELIST
    },
    'is_filter_user_info': {
        'display_name': '过滤关键字时是否附带发送者名称和ID',
        'values': {
            True: '是',
            False: '否'
        },
        'toggle_action': 'toggle_filter_user_info',
        'toggle_func': lambda current: not current
    },
    'forward_mode': {
        'display_name': '转发模式',
        'values': {
            ForwardMode.BLACKLIST: '仅黑名单',
            ForwardMode.WHITELIST: '仅白名单',
            ForwardMode.BLACKLIST_THEN_WHITELIST: '先黑名单后白名单',
            ForwardMode.WHITELIST_THEN_BLACKLIST: '先白名单后黑名单'
        },
        'toggle_action': 'toggle_forward_mode',
        'toggle_func': lambda current: {
            ForwardMode.BLACKLIST: ForwardMode.WHITELIST,
            ForwardMode.WHITELIST: ForwardMode.BLACKLIST_THEN_WHITELIST,
            ForwardMode.BLACKLIST_THEN_WHITELIST: ForwardMode.WHITELIST_THEN_BLACKLIST,
            ForwardMode.WHITELIST_THEN_BLACKLIST: ForwardMode.BLACKLIST
        }[current]
    },
    'use_bot': {
        'display_name': '转发方式',
        'values': {
            True: '使用机器人',
            False: '使用用户账号'
        },
        'toggle_action': 'toggle_bot',
        'toggle_func': lambda current: not current
    },
    'is_replace': {
        'display_name': '替换模式',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_replace',
        'toggle_func': lambda current: not current
    },
    'message_mode': {
        'display_name': '消息模式',
        'values': {
            MessageMode.MARKDOWN: 'Markdown',
            MessageMode.HTML: 'HTML'
        },
        'toggle_action': 'toggle_message_mode',
        'toggle_func': lambda current: MessageMode.HTML if current == MessageMode.MARKDOWN else MessageMode.MARKDOWN
    },
    'is_preview': {
        'display_name': '预览模式',
        'values': {
            PreviewMode.ON: '开启',
            PreviewMode.OFF: '关闭',
            PreviewMode.FOLLOW: '跟随原消息'
        },
        'toggle_action': 'toggle_preview',
        'toggle_func': lambda current: {
            PreviewMode.ON: PreviewMode.OFF,
            PreviewMode.OFF: PreviewMode.FOLLOW,
            PreviewMode.FOLLOW: PreviewMode.ON
        }[current]
    },
    'is_original_link': {
        'display_name': '原始链接',
        'values': {
            True: '附带',
            False: '不附带'
        },
        'toggle_action': 'toggle_original_link',
        'toggle_func': lambda current: not current
    },
    'is_delete_original': {
        'display_name': '删除原始消息',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_delete_original',
        'toggle_func': lambda current: not current
    },
    'is_ufb': {
        'display_name': 'UFB同步',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_ufb',
        'toggle_func': lambda current: not current
    },
    'is_original_sender': {
        'display_name': '原始发送者',
        'values': {
            True: '显示',
            False: '隐藏'
        },
        'toggle_action': 'toggle_original_sender',
        'toggle_func': lambda current: not current
    },
    'is_original_time': {
        'display_name': '发送时间',
        'values': {
            True: '显示',
            False: '隐藏'
        },
        'toggle_action': 'toggle_original_time',
        'toggle_func': lambda current: not current
    },
    'enable_delay': {
        'display_name': '延迟处理',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_delay',
        'toggle_func': lambda current: not current
    },
    'delay_seconds': {
        'values': {
            None: 5,
            '': 5
        },
        'toggle_action': 'set_delay_time',
        'toggle_func': None
    },
    'handle_mode': {
        'display_name': '处理模式',
        'values': {
            HandleMode.FORWARD: '转发模式',
            HandleMode.EDIT: '编辑模式'
        },
        'toggle_action': 'toggle_handle_mode',
        'toggle_func': lambda current: HandleMode.EDIT if current == HandleMode.FORWARD else HandleMode.FORWARD
    },
    'enable_comment_button': {
        'display_name': '查看评论区',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_comment_button',
        'toggle_func': lambda current: not current
    },
    'only_rss': {
        'display_name': '只转发到RSS',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_only_rss',
        'toggle_func': lambda current: not current
    },
    'close_settings': {
        'display_name': '关闭',
        'toggle_action': 'close_settings',
        'toggle_func': None
    },
    'enable_sync': {
        'display_name': '启用同步',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_sync',
        'toggle_func': lambda current: not current
    }
}


# 添加 AI 设置
AI_SETTINGS = {
    'is_ai': {
        'display_name': 'AI处理',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_ai',
        'toggle_func': lambda current: not current
    },
    'ai_model': {
        'display_name': 'AI模型',
        'values': {
            None: '默认',
            '': '默认',
            **{model: model for model in AI_MODELS}
        },
        'toggle_action': 'change_model',
        'toggle_func': None
    },
    'ai_prompt': {
        'display_name': '设置AI处理提示词',
        'toggle_action': 'set_ai_prompt',
        'toggle_func': None
    },
    'enable_ai_upload_image': {
        'display_name': '上传图片',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_ai_upload_image',
        'toggle_func': lambda current: not current
    },
    'is_keyword_after_ai': {
        'display_name': 'AI处理后再次执行关键字过滤',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_keyword_after_ai',
        'toggle_func': lambda current: not current
    },
    'is_summary': {
        'display_name': 'AI总结',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_summary',
        'toggle_func': lambda current: not current
    },
    'summary_time': {
        'display_name': '总结时间',
        'values': {
            None: '00:00',
            '': '00:00'
        },
        'toggle_action': 'set_summary_time',
        'toggle_func': None
    },
    'summary_prompt': {
        'display_name': '设置AI总结提示词',
        'toggle_action': 'set_summary_prompt',
        'toggle_func': None
    },
    'is_top_summary': {
        'display_name': '顶置总结消息',
        'values': {
            True: '是',
            False: '否'
        },
        'toggle_action': 'toggle_top_summary',
        'toggle_func': lambda current: not current
    },
    'summary_now': {
        'display_name': '立即执行总结',
        'toggle_action': 'summary_now',
        'toggle_func': None
    }

}

MEDIA_SETTINGS = {
    'enable_media_type_filter': {
        'display_name': '媒体类型过滤',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_media_type_filter',
        'toggle_func': lambda current: not current
    },
    'selected_media_types': {
        'display_name': '选择的媒体类型',
        'toggle_action': 'set_media_types',
        'toggle_func': None
    },
    'enable_media_size_filter': {
        'display_name': '媒体大小过滤',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_media_size_filter',
        'toggle_func': lambda current: not current
    },
    'max_media_size': {
        'display_name': '媒体大小限制',
        'values': {
            None: '5MB',
            '': '5MB'
        },
        'toggle_action': 'set_max_media_size',
        'toggle_func': None
    },
    'is_send_over_media_size_message': {
        'display_name': '媒体大小超限时发送提醒',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_send_over_media_size_message',
        'toggle_func': lambda current: not current
    },
    'enable_extension_filter': {
        'display_name': '媒体扩展名过滤',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_enable_media_extension_filter',
        'toggle_func': lambda current: not current
    },
    'extension_filter_mode': {
        'display_name': '媒体扩展名过滤模式',
        'values': {
            AddMode.BLACKLIST: '黑名单',
            AddMode.WHITELIST: '白名单'
        },
        'toggle_action': 'toggle_media_extension_filter_mode',
        'toggle_func': lambda current: AddMode.WHITELIST if current == AddMode.BLACKLIST else AddMode.BLACKLIST
    },
    'media_extensions': {
        'display_name': '设置媒体扩展名',
        'toggle_action': 'set_media_extensions',
        'toggle_func': None,
        'values': {}
    },
    'media_allow_text': {
        'display_name': '放行文本',
        'values': {
            True: '开启',
            False: '关闭'
        },
        'toggle_action': 'toggle_media_allow_text',
        'toggle_func': lambda current: not current
    }
}


OTHER_SETTINGS = {
    'copy_rule': {
        'display_name': '复制规则',
        'toggle_action': 'copy_rule',
        'toggle_func': None
    },
    'copy_keyword': {
        'display_name': '复制关键字',
        'toggle_action': 'copy_keyword',
        'toggle_func': None
    },
    'copy_replace': {
        'display_name': '复制替换',
        'toggle_action': 'copy_replace',
        'toggle_func': None
    },
    'clear_keyword': {
        'display_name': '清空所有关键字',
        'toggle_action': 'clear_keyword',
        'toggle_func': None
    },
    'clear_replace': {
        'display_name': '清空所有替换规则',
        'toggle_action': 'clear_replace',
        'toggle_func': None
    },
    'delete_rule': {
        'display_name': '删除规则',
        'toggle_action': 'delete_rule',
        'toggle_func': None
    },
    'null': {
        'display_name': '-----------',
        'toggle_action': 'null',
        'toggle_func': None
    },
    'set_userinfo_template': {
        'display_name': '设置用户信息模板',
        'toggle_action': 'set_userinfo_template',
        'toggle_func': None
    },
    'set_time_template': {
        'display_name': '设置时间模板',
        'toggle_action': 'set_time_template',
        'toggle_func': None
    },
    'set_original_link_template': {
        'display_name': '设置原始链接模板',
        'toggle_action': 'set_original_link_template',
        'toggle_func': None
    },
    'reverse_blacklist': {
        'display_name': '反转黑名单',
        'toggle_action': 'toggle_reverse_blacklist',
        'toggle_func': None
    },
    'reverse_whitelist': {
        'display_name': '反转白名单',
        'toggle_action': 'toggle_reverse_whitelist',
        'toggle_func': None
    }
}

PUSH_SETTINGS = {
    'enable_push_channel': {
        'display_name': '启用推送',
        'toggle_action': 'toggle_enable_push',
        'toggle_func': None
    },
    'add_push_channel': {
        'display_name': '➕ 添加推送配置',
        'toggle_action': 'add_push_channel',
        'toggle_func': None
    },
    'enable_only_push': {
        'display_name': '只转发到推送配置',
        'toggle_action': 'toggle_enable_only_push',
        'toggle_func': None
    }
}
