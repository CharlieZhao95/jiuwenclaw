# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Send Message tool - 发送短信工具.

包含：
- send_message: 通过手机发送短信
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
    name="send_message",
    description="""通过手机发送短信。需要提供接收方手机号码和短信内容。

功能说明：
- 手机号码会自动添加+86前缀（如果没有的话）
- 支持发送给国内手机号码

参数：
- phone_number: 接收方手机号码（会自动添加+86前缀）
- content: 短信内容

注意：
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多重试一次
""",
)
async def send_message(phone_number: str, content: str) -> Dict[str, Any]:
    """发送短信.

    Args:
        phone_number: 接收方手机号码（会自动添加+86前缀）
        content: 短信内容

    Returns:
        包含发送结果的响应字典
    """
    try:
        logger.info(f"[SEND_MESSAGE_TOOL] Starting exec - phone_number: {phone_number}, content len: {len(content)}")

        # 验证参数
        if not phone_number or not isinstance(phone_number, str):
            raise ToolInputError("缺少必填参数 phone_number（接收方手机号码）")

        if not content or not isinstance(content, str):
            raise ToolInputError("缺少必填参数 content（短信内容）")

        phone_number = phone_number.strip()
        content = content.strip()

        if not phone_number:
            raise ToolInputError("phone_number 不能为空")

        if not content:
            raise ToolInputError("content 不能为空")

        # 规范化手机号码：添加 +86 前缀
        if not phone_number.startswith("+86"):
            # 移除开头的 0
            if phone_number.startswith("0"):
                phone_number = phone_number[1:]
            # 避免重复添加 86 前缀
            if phone_number.startswith("86"):
                phone_number = phone_number[2:]
            phone_number = f"+86{phone_number}"

        logger.info(f"[SEND_MESSAGE_TOOL] Normalized phone number: {phone_number}")

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
                    "intentName": "SendShortMessage",
                    "bundleName": "com.huawei.hmos.aidispatchservice",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "phoneNumber": phone_number,
                        "content": content,
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
        outputs = await execute_device_command("SendShortMessage", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"发送短信失败: {error_msg} (错误代码: {code})")

        # 提取结果
        result = outputs.get("result", {})

        logger.info("[SEND_MESSAGE_TOOL] Message sent successfully")

        return format_success_response(
            {
                "success": True,
                "phoneNumber": phone_number,
                "result": result,
            },
            f"短信已发送至 {phone_number}"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[SEND_MESSAGE_TOOL] Failed to send message: {e}")
        raise RuntimeError(f"发送短信失败: {str(e)}") from e
