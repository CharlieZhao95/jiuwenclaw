# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Xiaoyi Handset Tools - 小艺手机端设备工具.

该目录包含需要连接小艺手机端设备才能使用的工具。
这些工具通过 WebSocket 与手机端通信，调用设备原生能力。

工具分类：
- 定位: get_user_location
- 备忘录: create_note, search_notes, modify_note
- 日历: create_calendar_event, search_calendar
- 联系人: search_contacts
- 相册: search_photo_gallery, upload_photo
- 文件: search_files, upload_files, send_file_to_user
- 电话: call_phone
- 短信: send_message
- 消息: search_messages
- 闹钟: create_alarm, search_alarms, modify_alarm, delete_alarm
- 收藏: xiaoyi_collection
"""

from .location_tool import get_user_location
from .note_tools import create_note, search_notes, modify_note
from .calendar_tools import create_calendar_event, search_calendar
from .contact_tools import search_contacts
from .photo_tools import search_photo_gallery, upload_photo
from .file_tools import search_files, upload_files, send_file_to_user
from .phone_tools import call_phone
from .send_message_tool import send_message
from .message_tools import search_messages
from .alarm_tools import create_alarm, search_alarms, modify_alarm, delete_alarm
from .collection_tool import xiaoyi_collection

__all__ = [
    "get_user_location",
    "create_note",
    "search_notes",
    "modify_note",
    "create_calendar_event",
    "search_calendar",
    "search_contacts",
    "search_photo_gallery",
    "upload_photo",
    "search_files",
    "upload_files",
    "send_file_to_user",
    "call_phone",
    "send_message",
    "search_messages",
    "create_alarm",
    "search_alarms",
    "modify_alarm",
    "delete_alarm",
    "xiaoyi_collection",
]

