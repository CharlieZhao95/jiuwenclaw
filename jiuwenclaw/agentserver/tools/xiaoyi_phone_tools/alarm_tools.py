# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Alarm tools - 闹钟工具.

包含：
- create_alarm: 创建闹钟
- search_alarms: 搜索闹钟
- modify_alarm: 修改闹钟
- delete_alarm: 删除闹钟
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    format_success_response,
    ToolInputError,
)


@tool(
    name="create_alarm",
    description="""在用户设备上创建闹钟。需要提供闹钟时间和可选的重复设置。

时间格式：hh:mm（24小时制，例如 07:30 或 14:00）

参数说明：
- hour: 小时（0-23）
- minute: 分钟（0-59）
- repeat: 重复设置，如 "monday,tuesday"（可选）
- label: 闹钟标签/名称（可选）

注意：
- 操作超时时间为60秒，请勿重复调用
- 如果创建失败，最多只能重试一次
""",
)
async def create_alarm(
    hour: int,
    minute: int,
    repeat: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """创建闹钟.

    Args:
        hour: 小时（0-23），必填
        minute: 分钟（0-59），必填
        repeat: 重复设置，如 "monday,tuesday,weekday,weekend,everyday"（可选）
        label: 闹钟标签（可选）

    Returns:
        包含创建结果的响应字典
    """
    try:
        logger.info(f"[ALARM_TOOL] Creating alarm - time: {hour:02d}:{minute:02d}")

        # 验证参数
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ToolInputError("hour 必须是 0-23 的整数")
        if not isinstance(minute, int) or minute < 0 or minute > 59:
            raise ToolInputError("minute 必须是 0-59 的整数")

        # 构建参数
        intent_param = {"hour": hour, "minute": minute}
        if repeat:
            intent_param["repeat"] = repeat
        if label:
            intent_param["label"] = label

        # 构建命令 - 与 xy_channel 保持一致
        command = {
            "header": {
                "namespace": "Common",
                "name": "Action",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "CreateAlarm",
                    "bundleName": "com.huawei.hmos.clock",
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
        outputs = await execute_device_command("CreateAlarm", command)

        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"创建闹钟失败: {error_msg} (错误代码: {code})")

        result = outputs.get("result", {})
        time_str = f"{hour:02d}:{minute:02d}"
        logger.info(f"[ALARM_TOOL] Alarm created successfully at {time_str}")

        return format_success_response(
            {
                "success": True,
                "alarm": {
                    "entityId": result.get("entityId"),
                    "entityName": result.get("entityName"),
                    "alarmTitle": result.get("alarmTitle"),
                    "alarmTime": result.get("alarmTime"),
                    "alarmState": result.get("alarmState"),
                    "alarmRingDuration": result.get("alarmRingDuration"),
                    "alarmSnoozeDuration": result.get("alarmSnoozeDuration"),
                    "alarmSnoozeTotal": result.get("alarmSnoozeTotal"),
                    "daysOfWakeType": result.get("daysOfWakeType"),
                },
                "code": code,
            },
            f"闹钟 {time_str} 创建成功"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[ALARM_TOOL] Failed to create alarm: {e}")
        raise RuntimeError(f"创建闹钟失败: {str(e)}") from e


@tool(
    name="search_alarms",
    description="""在用户设备上搜索闹钟。

注意：
- 操作超时时间为60秒，请勿重复调用
- 返回设备上所有闹钟的列表
""",
)
async def search_alarms() -> Dict[str, Any]:
    """搜索闹钟.

    Returns:
        包含闹钟列表的响应字典
    """
    try:
        logger.info("[ALARM_TOOL] Searching alarms")

        # 构建命令 - 与 xy_channel 保持一致
        command = {
            "header": {
                "namespace": "Common",
                "name": "Action",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "SearchAlarm",
                    "bundleName": "com.huawei.hmos.clock",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {"rangeType": "all"},  # 查询所有闹钟
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
        outputs = await execute_device_command("SearchAlarm", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"检索闹钟失败: {error_msg} (错误代码: {code})")

        # 提取结果（items 可能是 JSON 字符串数组，需要解析）
        result = outputs.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []

        # 解析 JSON 字符串
        parsed_alarms = []
        for item in items:
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    parsed_alarms.append(parsed)
                except json.JSONDecodeError:
                    logger.warning(f"[ALARM_TOOL] 无法解析闹钟项: {item}")
            elif isinstance(item, dict):
                parsed_alarms.append(item)

        logger.info(f"[ALARM_TOOL] Found {len(parsed_alarms)} alarms")

        return format_success_response(
            {"alarms": parsed_alarms, "count": len(parsed_alarms)},
            f"找到 {len(parsed_alarms)} 个闹钟"
        )

    except Exception as e:
        logger.error(f"[ALARM_TOOL] Failed to search alarms: {e}")
        raise RuntimeError(f"搜索闹钟失败: {str(e)}") from e


@tool(
    name="modify_alarm",
    description="""在用户设备上修改闹钟。需要提供闹钟ID和要修改的参数。

参数说明：
- alarm_id: 闹钟ID（必填）
- hour: 新小时（可选）
- minute: 新分钟（可选）
- repeat: 新重复设置（可选）
- label: 新标签（可选）
- enabled: 是否启用（可选，true/false）

注意：
- 操作超时时间为60秒，请勿重复调用
""",
)
async def modify_alarm(
    alarm_id: str,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    repeat: Optional[str] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """修改闹钟.

    Args:
        alarm_id: 闹钟ID，必填
        hour: 新小时（可选）
        minute: 新分钟（可选）
        repeat: 新重复设置（可选）
        label: 新标签（可选）
        enabled: 是否启用（可选）

    Returns:
        包含修改结果的响应字典
    """
    try:
        logger.info(f"[ALARM_TOOL] Modifying alarm - alarm_id: {alarm_id}")

        # 验证参数
        if not alarm_id:
            raise ToolInputError("缺少必填参数 alarm_id（闹钟ID）")

        # 构建参数
        intent_param = {"alarmId": alarm_id}
        if hour is not None:
            intent_param["hour"] = hour
        if minute is not None:
            intent_param["minute"] = minute
        if repeat:
            intent_param["repeat"] = repeat
        if label:
            intent_param["label"] = label
        if enabled is not None:
            intent_param["enabled"] = enabled

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
                    "intentName": "ModifyAlarm",
                    "bundleName": "com.huawei.hmos.clock",
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
        outputs = await execute_device_command("ModifyAlarm", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"修改闹钟失败: {error_msg} (错误代码: {code})")

        result = outputs.get("result", {})

        logger.info("[ALARM_TOOL] Alarm modified successfully")

        return format_success_response(
            {
                "alarm_id": alarm_id,
                "entityId": result.get("entityId"),
                "alarmTitle": result.get("alarmTitle"),
                "alarmState": result.get("alarmState"),
            },
            "闹钟修改成功"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[ALARM_TOOL] Failed to modify alarm: {e}")
        raise RuntimeError(f"修改闹钟失败: {str(e)}") from e


@tool(
    name="delete_alarm",
    description="""在用户设备上删除闹钟。

参数说明：
- alarm_id: 要删除的闹钟ID（必填）

注意：
- 操作超时时间为60秒，请勿重复调用
- 删除后无法恢复
""",
)
async def delete_alarm(alarm_id: str) -> Dict[str, Any]:
    """删除闹钟.

    Args:
        alarm_id: 闹钟ID，必填

    Returns:
        包含删除结果的响应字典
    """
    try:
        logger.info("[ALARM_TOOL] 🗑️ Deleting alarm")
        logger.info(f"[ALARM_TOOL]   - alarm_id: {alarm_id}")

        # 验证参数
        if not alarm_id:
            raise ToolInputError("缺少必填参数 alarm_id（闹钟ID）")

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
                    "intentName": "DeleteAlarm",
                    "bundleName": "com.huawei.hmos.clock",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {"alarmId": alarm_id},
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
        outputs = await execute_device_command("DeleteAlarm", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"删除闹钟失败: {error_msg} (错误代码: {code})")

        result = outputs.get("result", {})

        logger.info("[ALARM_TOOL] Alarm deleted successfully")

        return format_success_response(
            {
                "alarm_id": alarm_id,
                "entityId": result.get("entityId"),
                "success": True,
            },
            "闹钟已删除"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[ALARM_TOOL] Failed to delete alarm: {e}")
        raise RuntimeError(f"删除闹钟失败: {str(e)}") from e
