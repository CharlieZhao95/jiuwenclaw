# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Phone tools - 电话工具.

包含：
- call_phone: 拨打电话
"""

from __future__ import annotations

from typing import Any, Dict

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    format_success_response,
    ToolInputError,
)


@tool(
    name="call_phone",
    description="""拨打电话。需要提供要拨打的电话号码。

参数说明：
- phoneNumber: 要拨打的电话号码（必填）
- slotId: SIM卡槽ID，默认为0（主卡），设置为1表示副卡。仅当用户明确要求使用副卡时才设置为1

注意：
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多重试一次
""",
)
async def call_phone(phone_number: str, slot_id: int = 0) -> Dict[str, Any]:
    """拨打电话.

    Args:
        phone_number: 要拨打的电话号码，必填
        slot_id: SIM卡槽ID，0=主卡（默认），1=副卡

    Returns:
        包含拨打结果的响应字典
    """
    try:
        logger.info(f"[PHONE_TOOL] Calling phone number - phone_number: {phone_number}, slot_id: {slot_id}")

        # 验证参数
        if not phone_number or not isinstance(phone_number, str):
            raise ToolInputError("缺少必填参数 phoneNumber（电话号码）")

        phone_number = phone_number.strip()
        if not phone_number:
            raise ToolInputError("phoneNumber 不能为空")

        # 验证 slot_id
        if slot_id not in [0, 1]:
            raise ToolInputError("slotId 必须是 0（主卡）或 1（副卡）")

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
                    "intentName": "StartCall",
                    "bundleName": "com.huawei.hmos.aidispatchservice",
                    "dimension": "",
                    "needUnlock": True,
                    "actionResponse": True,
                    "timeOut": 5,
                    "intentParam": {
                        "phoneNumber": phone_number,
                        "slotId": slot_id,
                    },
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
        outputs = await execute_device_command("StartCall", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"拨打电话失败: {error_msg} (错误代码: {code})")

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"拨打电话失败: {error_msg} (错误代码: {code})")

        result = outputs.get("result", {})

        sim_name = "主卡" if slot_id == 0 else "副卡"
        logger.info(f"[PHONE_TOOL] Call initiated successfully via {sim_name}")

        return format_success_response(
            {
                "phone_number": phone_number,
                "slot_id": slot_id,
                "sim": sim_name,
                "success": True,
                "callState": result.get("callState"),
            },
            f"正在使用{sim_name}拨打 {phone_number}..."
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[PHONE_TOOL] Failed to initiate call: {e}")
        raise RuntimeError(f"拨打电话失败: {str(e)}") from e
