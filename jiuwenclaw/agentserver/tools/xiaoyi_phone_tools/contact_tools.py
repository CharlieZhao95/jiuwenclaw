# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Contact tools - 联系人工具.

包含：
- search_contacts: 搜索联系人
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
    name="search_contacts",
    description="""搜索用户设备上的联系人信息。根据姓名在通讯录中检索联系人详细信息（包括姓名、电话号码、邮箱、组织、职位等）。

注意：
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多重试一次
""",
)
async def search_contacts(
    name: str,
) -> Dict[str, Any]:
    """搜索联系人.

    Args:
        name: 联系人姓名，用于在通讯录中检索联系人信息

    Returns:
        包含联系人列表的响应字典
    """
    try:
        logger.info(f"[CONTACT_TOOL] Searching contacts - name: {name}")

        # 验证参数
        if not name or not isinstance(name, str):
            raise ToolInputError("缺少必填参数 name（联系人姓名）")

        name = name.strip()
        if not name:
            raise ToolInputError("name 不能为空")

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
                    "intentName": "SearchContactLocal",
                    "bundleName": "com.huawei.hmos.aidispatchservice",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "name": name,
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
        outputs = await execute_device_command("SearchContactLocal", command)

        # 检查错误码
        ret_err_code = outputs.get("retErrCode")
        if ret_err_code and ret_err_code != "0":
            err_msg = outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"搜索联系人失败: {err_msg} (错误码: {ret_err_code})")

        # 提取结果
        result = outputs.get("result", {})

        logger.info(f"[CONTACT_TOOL] found {len(result.get('items', [])) if isinstance(result, dict) else 0} contacts")

        return format_success_response(
            {"result": result},
            f"搜索到联系人信息"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[CONTACT_TOOL] Failed to search contacts: {e}")
        raise RuntimeError(f"搜索联系人失败: {str(e)}") from e
