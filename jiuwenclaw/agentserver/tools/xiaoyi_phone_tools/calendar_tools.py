# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Calendar tools - 日历工具.

包含：
- create_calendar_event: 创建日程
- search_calendar: 搜索日程
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from openjiuwen.core.foundation.tool import tool


def _format_timestamp_to_datetime(timestamp_ms: int) -> str:
    """将毫秒时间戳转换为 yyyy-mm-dd hh:mm:ss 格式.

    Args:
        timestamp_ms: 毫秒时间戳

    Returns:
        格式化的日期时间字符串
    """
    if not timestamp_ms:
        return ""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _convert_event_timestamps(event: Dict[str, Any]) -> Dict[str, Any]:
    """将事件中的时间戳转换为可读格式.

    Args:
        event: 日程事件字典

    Returns:
        转换后的事件字典
    """
    result = dict(event)
    if "dtStart" in result and result["dtStart"]:
        result["dtStart"] = _format_timestamp_to_datetime(result["dtStart"])
    if "dtEnd" in result and result["dtEnd"]:
        result["dtEnd"] = _format_timestamp_to_datetime(result["dtEnd"])
    return result

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    validate_required_params,
    format_success_response,
    format_error_response,
    ToolInputError,
)


@tool(
    name="create_calendar_event",
    description="""在用户设备上创建日程。需要提供日程标题、开始时间和结束时间。

时间格式必须为：yyyy-mm-dd hh:mm:ss（例如：2024-01-15 14:30:00）。

注意：
- 该工具执行时间较长（最多60秒），请勿重复调用
- 超时或失败时最多重试一次
- 使用该工具之前需获取当前真实时间
""",
)
async def create_calendar_event(
    title: str,
    dt_start: str,
    dt_end: str,
    location: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """创建日程.

    Args:
        title: 日程标题/名称，必填
        dt_start: 开始时间，格式 yyyy-mm-dd hh:mm:ss
        dt_end: 结束时间，格式 yyyy-mm-dd hh:mm:ss
        location: 地点（可选）
        description: 描述（可选）

    Returns:
        包含创建结果的响应字典
    """
    try:
        logger.info(f"[CALENDAR_TOOL]  Create calendar event - title: {title}, dt_start: {dt_start}, dt_end: {dt_end}")

        # 验证参数
        if not title:
            raise ToolInputError("缺少必填参数 title（日程标题）")
        if not dt_start:
            raise ToolInputError("缺少必填参数 dt_start（开始时间）")
        if not dt_end:
            raise ToolInputError("缺少必填参数 dt_end（结束时间）")

        # 转换时间字符串为时间戳
        try:
            start_dt = datetime.strptime(dt_start, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(dt_end, "%Y-%m-%d %H:%M:%S")
            dt_start_ms = int(start_dt.timestamp() * 1000)
            dt_end_ms = int(end_dt.timestamp() * 1000)
        except ValueError:
            raise ToolInputError(
                "时间格式错误。必须使用：yyyy-mm-dd hh:mm:ss（例如：2024-01-15 14:30:00）"
            ) from ValueError

        # 构建参数
        intent_param = {
            "title": title,
            "dtStart": dt_start_ms,
            "dtEnd": dt_end_ms,
        }
        if location:
            intent_param["location"] = location
        if description:
            intent_param["description"] = description

        # 构建命令
        command = {
            "header": {
                "namespace": "Common",
                "name": "ActionAndResult",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "CreateCalendarEvent",
                    "bundleName": "com.huawei.hmos.calendardata",
                    "dimension": "",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": intent_param,
                    "permissionId": [],
                    "achieveType": "INTENT",
                },
                "responses": [{"resultCode": "", "displayText": "", "ttsText": ""}],
                "needUploadResult": True,
                "noHalfPage": False,
                "pageControlRelated": False,
            },
        }

        # 执行命令
        result = await execute_device_command("CreateCalendarEvent", command)

        logger.info("[CALENDAR_TOOL] Calendar event created successfully")
        return format_success_response(
            {"title": title, "dt_start": dt_start, "dt_end": dt_end, "result": result},
            f"日程 '{title}' 创建成功"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[CALENDAR_TOOL] Failed to create calendar event: {e}")
        raise RuntimeError(f"创建日程失败: {str(e)}") from e


@tool(
    name="search_calendar",
    description="""在用户设备上搜索日程。可以按标题、时间范围搜索。

时间格式：yyyy-mm-dd hh:mm:ss

注意：
- 操作超时时间为60秒，请勿重复调用
- 如果搜索失败，最多只能重试一次
""",
)
async def search_calendar(
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """搜索日程.

    Args:
        keyword: 搜索关键词（可选）
        start_time: 开始时间范围（可选）
        end_time: 结束时间范围（可选）
        max_results: 最大返回结果数，默认10

    Returns:
        包含日程列表的响应字典
    """
    try:
        logger.info(f"[CALENDAR_TOOL] Searching calendar events - keyword: {keyword}")

        # 构建参数 - 使用 timeInterval 数组格式（与 xy_channel 一致）
        intent_param: Dict[str, Any] = {}

        # 转换时间格式
        start_time_ms = 0
        end_time_ms = 0

        if start_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                start_time_ms = int(start_dt.timestamp() * 1000)
            except ValueError:
                raise ToolInputError("start_time 格式错误，必须使用：yyyy-mm-dd hh:mm:ss") from ValueError

        if end_time:
            try:
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                end_time_ms = int(end_dt.timestamp() * 1000)
            except ValueError:
                raise ToolInputError("end_time 格式错误，必须使用：yyyy-mm-dd hh:mm:ss") from ValueError

        # 使用 timeInterval 数组格式
        if start_time_ms and end_time_ms:
            intent_param["timeInterval"] = [start_time_ms, end_time_ms]

        if keyword:
            intent_param["title"] = keyword

        # 构建命令
        command = {
            "header": {
                "namespace": "Common",
                "name": "Action",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "SearchCalendarEvent",
                    "bundleName": "com.huawei.hmos.calendardata",
                    "dimension": "",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": intent_param,
                    "permissionId": [],
                    "achieveType": "INTENT",
                },
                "responses": [{"resultCode": "", "displayText": "", "ttsText": ""}],
                "needUploadResult": True,
                "noHalfPage": False,
                "pageControlRelated": False,
            },
        }

        # 执行命令
        outputs = await execute_device_command("SearchCalendarEvent", command)

        # 检查错误码
        if outputs.get("retErrCode") and outputs.get("retErrCode") != "0":
            err_msg = outputs.get("errMsg", "未知错误")
            raise RuntimeError(f"检索日程失败: {err_msg} (错误代码: {outputs['retErrCode']})")

        # 获取结果
        result = outputs.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []

        # 转换时间戳为可读格式
        formatted_items = [_convert_event_timestamps(item) for item in items]

        logger.info(f"[CALENDAR_TOOL] Found {len(formatted_items)} events")

        return format_success_response(
            {"events": formatted_items, "count": len(formatted_items)},
            f"搜索到 {len(formatted_items)} 条日程"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[CALENDAR_TOOL] Failed to search calendar: {e}")
        raise RuntimeError(f"搜索日程失败: {str(e)}") from e
