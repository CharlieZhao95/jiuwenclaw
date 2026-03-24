# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Location tool - 获取手机当前定位.

通过 WebSocket 发送 GetCurrentLocation 指令到手机端，
手机端执行系统定位后返回经纬度坐标。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import execute_device_command, format_success_response


@tool(
    name="get_user_location",
    description=(
        "获取用户当前位置（经纬度坐标，WGS84坐标系）。"
        "需要用户设备授权位置访问权限。"
        "注意:操作超时时间为60秒,请勿重复调用此工具,如果超时或失败,最多重试一次。"
    ),
)
async def get_user_location() -> Dict[str, List[Dict[str, str]]]:
    """获取用户当前地理位置.

    Returns:
        包含 content 数组的字典，content 中包含 type 和 text 字段
        text 字段是 JSON 字符串，包含 latitude、longitude 和 coordinateSystem
    """

    # Build GetCurrentLocation command
    logger.info("[LOCATION_TOOL] Starting execution - Building GetCurrentLocation command...")
    command = {
        "header": {
            "namespace": "Common",
            "name": "Action",
        },
        "payload": {
            "cardParam": {},
            "executeParam": {
                "achieveType": "INTENT",
                "actionResponse": True,
                "bundleName": "com.huawei.hmos.aidispatchservice",
                "dimension": "",
                "executeMode": "background",
                "intentName": "GetCurrentLocation",
                "intentParam": {},
                "needUnlock": True,
                "appType": "OHOS_APP",
                "permissionId": [],
                "timeOut": 5,
            },
            "needUploadResult": True,
            "noHalfPage": False,
            "pageControlRelated": False,
            "responses": [{
                "displayText": "",
                "resultCode": "",
                "ttsText": "",
            }],
        },
    }

    # Execute command and get result
    logger.info("[LOCATION_TOOL] Waiting for location response...")
    outputs = await execute_device_command("GetCurrentLocation", command)

    latitude = outputs.get("latitude")
    longitude = outputs.get("longitude")

    logger.info(f"[LOCATION_TOOL] Location retrieved successfully - latitude: {latitude}, longitude: {longitude}")

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "latitude": latitude,
                    "longitude": longitude,
                    "coordinateSystem": "WGS84",
                })
            }
        ]
    }
