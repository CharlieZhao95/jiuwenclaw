# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Note tools - 备忘录工具.

包含：
- create_note: 创建备忘录
- search_notes: 搜索备忘录
- modify_note: 修改备忘录
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    validate_required_params,
    format_success_response,
    format_error_response,
    ToolInputError,
)


@tool(
    name="create_note",
    description="""在用户设备上创建备忘录。需要提供备忘录标题和内容。

注意:
- 操作超时时间为60秒，请勿重复调用此工具
- 如果遇到各类调用失败场景，最多只能重试一次，不可以重复调用多次
- 调用工具前需认真检查调用参数是否满足工具要求
""",
)
async def create_note(title: str, content: str) -> Dict[str, Any]:
    """创建备忘录.

    Args:
        title: 备忘录标题，必填
        content: 备忘录内容，必填

    Returns:
        包含创建结果的响应字典
    """
    try:
        logger.info(f"[NOTE_TOOL] Creating note - title: {title}")

        # 验证参数
        if not title or not isinstance(title, str):
            raise ToolInputError("缺少必填参数 title（备忘录标题）")
        if not content or not isinstance(content, str):
            raise ToolInputError("缺少必填参数 content（备忘录内容）")

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
                    "intentName": "CreateNote",
                    "bundleName": "com.huawei.hmos.notepad",
                    "dimension": "",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "title": title,
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
        outputs = await execute_device_command("CreateNote", command)

        # 提取结果（与 xy_channel 一致）
        result = outputs.get("result", {})
        code = outputs.get("code", "")

        logger.info(f"[NOTE_TOOL] Note created: title={result.get('title')}, id={result.get('entityId')}")

        return format_success_response(
            {
                "success": True,
                "note": {
                    "entityId": result.get("entityId"),
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "entityName": result.get("entityName"),
                    "modifiedDate": result.get("modifiedDate"),
                },
                "code": code,
            },
            f"备忘录 '{title}' 创建成功"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[NOTE_TOOL] Failed to create note: {e}")
        raise RuntimeError(f"创建备忘录失败: {str(e)}") from e


@tool(
    name="search_notes",
    description="""在用户设备上搜索备忘录。可以通过关键词搜索标题或内容。

注意:
- 操作超时时间为60秒，请勿重复调用此工具
- 如果搜索失败，最多只能重试一次
""",
)
async def search_notes(keyword: str, max_results: int = 10) -> Dict[str, Any]:
    """搜索备忘录.

    Args:
        keyword: 搜索关键词
        max_results: 最大返回结果数，默认10

    Returns:
        包含备忘录列表的响应字典
    """
    try:
        logger.info(f"[NOTE_TOOL] Searching notes - keyword: {keyword}")

        # 构建命令 - 与 xy_channel search-note-tool.ts 保持一致
        command = {
            "header": {
                "namespace": "Common",
                "name": "Action",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "SearchNote",
                    "bundleName": "com.huawei.hmos.notepad",
                    "dimension": "",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "query": keyword,  # xy_channel 使用 query 而非 keyword
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
        outputs = await execute_device_command("SearchNote", command)

        # 检查结果结构（与 xy_channel 一致）
        result = outputs.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []

        logger.info(f"[NOTE_TOOL] Found {len(items)} notes")

        # 格式化结果（移除 <em> 标签等）
        formatted_notes = []
        for item in items:
            formatted_notes.append({
                "entityId": item.get("entityId"),
                "entityName": item.get("entityName"),
                "title": item.get("title", "").replace("</?em>", ""),  # 移除 <em> 标签
                "content": item.get("content"),
                "createdDate": item.get("createdDate"),
                "modifiedDate": item.get("modifiedDate"),
            })

        return format_success_response(
            {
                "notes": formatted_notes,
                "count": len(formatted_notes),
                "query": keyword,
                "totalResults": len(formatted_notes),
            },
            f"搜索到 {len(formatted_notes)} 条备忘录"
        )

    except Exception as e:
        logger.error(f"[NOTE_TOOL] Failed to search notes: {e}")
        raise RuntimeError(f"搜索备忘录失败: {str(e)}") from e


@tool(
    name="modify_note",
    description="""在指定备忘录中追加新内容。使用前必须先调用 search_notes 工具获取备忘录的 entityId。

参数说明：
- entity_id: 备忘录的唯一标识符（从 search_notes 工具获取）
- text: 要追加的文本内容

注意:
- 操作超时时间为60秒，请勿重复调用此工具
- 如果超时或失败，最多只能重试一次
""",
)
async def modify_note(
    entity_id: str,
    text: str,
) -> Dict[str, Any]:
    """修改备忘录（追加模式）.

    Args:
        entity_id: 备忘录的唯一标识符（从 search_notes 获取），必填
        text: 要追加的文本内容，必填

    Returns:
        包含修改结果的响应字典
    """
    try:
        logger.info(f"[NOTE_TOOL] Modifying note - entity_id: {entity_id}")

        # 验证参数
        if not entity_id:
            raise ToolInputError("缺少必填参数 entity_id（备忘录ID）")
        if not text or not isinstance(text, str):
            raise ToolInputError("缺少必填参数 text（要追加的文本内容）")

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
                    "intentName": "ModifyNote",
                    "bundleName": "com.huawei.hmos.notepad",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "contentType": "1",  # 1 = 追加模式 (append mode)
                        "text": text,
                        "entityId": entity_id,
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
        outputs = await execute_device_command("ModifyNote", command)

        # 提取结果
        result = outputs.get("result", {})

        logger.info("[NOTE_TOOL] Note modified successfully")
        return format_success_response(
            {
                "entity_id": entity_id,
                "entityId": result.get("entityId"),
                "title": result.get("title"),
                "modifiedDate": result.get("modifiedDate"),
            },
            "备忘录修改成功"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[NOTE_TOOL] Failed to modify note: {e}")
        raise RuntimeError(f"修改备忘录失败: {str(e)}") from e
