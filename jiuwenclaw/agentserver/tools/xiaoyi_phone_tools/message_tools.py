# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Message tools - 消息工具.

包含：
- search_messages: 搜索消息
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    format_success_response,
    ToolInputError,
)


@tool(
    name="search_messages",
    description="""搜索手机短信。根据关键词搜索短信内容。

注意：
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多重试一次
""",
)
async def search_messages(
    content: str,
) -> Dict[str, Any]:
    """搜索短信消息.

    Args:
        content: 搜索关键词，用于在短信内容中进行匹配

    Returns:
        包含消息列表的响应字典
    """
    try:
        logger.info(f"[MESSAGE_TOOL] Searching messages - content: {content}")

        # 验证参数
        if not content or not isinstance(content, str):
            raise ToolInputError("缺少必填参数 content（搜索关键词）")

        content = content.strip()
        if not content:
            raise ToolInputError("content 不能为空")

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
                    "intentName": "SearchMessage",
                    "bundleName": "com.huawei.hmos.aidispatchservice",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
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
        outputs = await execute_device_command("SearchMessage", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"搜索短信失败: {error_msg} (错误代码: {code})")

        # 提取结果
        result = outputs.get("result", {})
        messages = result.get("items", []) if isinstance(result, dict) else []

        logger.info(f"[MESSAGE_TOOL] Found {len(messages)} messages")

        return format_success_response(
            {"messages": messages, "count": len(messages)},
            f"搜索到 {len(messages)} 条消息"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[MESSAGE_TOOL] Failed to search messages: {e}")
        raise RuntimeError(f"搜索消息失败: {str(e)}") from e
