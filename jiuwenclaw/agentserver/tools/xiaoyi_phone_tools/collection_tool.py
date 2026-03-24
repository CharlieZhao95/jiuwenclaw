# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Collection tool - 小艺收藏工具.

包含：
- xiaoyi_collection: 检索用户在小艺收藏中记下来的公共知识数据
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
    name="xiaoyi_collection",
    description="""检索用户在小艺收藏中记下来的公共知识数据，可以给用户提供个性化体验。

使用场景：
- 当用户语料中涉及"从我的小艺收藏"、"查看我的收藏"、"我xx时候收藏的xxx帮我看一下"等语料时需要使用此工具
- 用户想查看自己之前收藏的信息时

参数：
- query_all: 是否查询所有收藏数据，默认为"true"

注意：
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多重试一次
""",
)
async def xiaoyi_collection(query_all: str = "true") -> Dict[str, Any]:
    """检索小艺收藏.

    Args:
        query_all: 是否查询所有收藏数据，默认为"true"

    Returns:
        包含收藏列表的响应字典
    """
    try:
        logger.info(f"[COLLECTION_TOOL] Starting execution - query_all: {query_all}")

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
                    "intentName": "QueryCollection",
                    "bundleName": "com.huawei.hmos.vassistant",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "queryAll": query_all,
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
        outputs = await execute_device_command("QueryCollection", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            raise RuntimeError(f"查询小艺收藏失败 (错误码: {code})")

        # 提取结果
        result = outputs.get("result", {})

        if not result:
            logger.warning("[COLLECTION_TOOL] No collection data found")
            return format_success_response(
                {
                    "success": True,
                    "memoryInfo": [],
                    "message": "未找到收藏数据"
                },
                "未找到收藏数据"
            )

        # 提取 memoryInfo 从嵌套结构
        memory_info = result.get("result", {}).get("memoryInfo", []) if isinstance(result, dict) else []

        logger.info(f"[COLLECTION_TOOL] Found {len(memory_info)} collections")

        # 简化和格式化收藏数据
        simplified_collections = []
        for item in memory_info:
            simplified_collections.append({
                "uuid": item.get("uuid"),
                "type": item.get("type"),
                "status": item.get("status"),
                "collectionTime": item.get("collectionTime"),
                "editTime": item.get("editTime"),
                "title": item.get("linkTitle") or item.get("aiTitle") or item.get("textTitle") or
                         item.get("imageTitle") or item.get("podcastTitle") or "",
                "description": item.get("description") or item.get("abstract") or "",
                "content": item.get("textContent") or "",
                "linkUrl": item.get("linkUrl"),
                "linkType": item.get("linkType"),
                "appName": item.get("appNameFromPab") or item.get("appName") or "",
                "labels": item.get("label") or [],
                "collectionMethod": item.get("collectionMethod"),
            })

        return format_success_response(
            {
                "success": True,
                "totalResults": len(simplified_collections),
                "collections": simplified_collections,
                "message": result.get("message") if isinstance(result, dict) else None,
            },
            f"找到 {len(simplified_collections)} 条收藏记录"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[COLLECTION_TOOL] Failed to query collection: {e}")
        raise RuntimeError(f"查询小艺收藏失败: {str(e)}") from e
