# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""File tools - 文件工具.

包含：
- search_files: 搜索文件
- upload_files: 上传文件
- send_file_to_user: 发送文件给用户
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openjiuwen.core.foundation.tool import tool

from jiuwenclaw.utils import logger
from .base import (
    execute_device_command,
    format_success_response,
    ToolInputError,
)


@tool(
    name="search_files",
    description="""搜索手机文件系统的文件。

【重要】使用约束：此工具仅在用户显著说明要从手机搜索时才执行，例如：
- "从我手机里面搜索xxxx"
- "从手机文件系统找一下xxxx"
- "在手机上查找文件xxxx"
- "搜索手机里的文件"

如果用户没有明确说明从手机搜索（如仅说"搜索文件"、"找一下xxxx"），应默认从 openclaw 本地的文件系统查询，不要调用此工具。

功能说明：根据关键词搜索文件名称或内容，返回匹配的文件列表（包括文件名、路径、大小、修改时间等信息）。

注意：
- 操作超时时间为60秒，请勿重复调用此工具，如果超时或失败，最多重试一次
""",
)
async def search_files(
    query: str,
) -> Dict[str, Any]:
    """搜索文件.

    Args:
        query: 搜索关键词，用于匹配文件名称、后缀名或文件内容

    Returns:
        包含文件列表的响应字典
    """
    try:
        logger.info(f"[FILE_TOOL] Searching files - query: {query}")

        # 验证参数
        if not query or not isinstance(query, str):
            raise ToolInputError("缺少必填参数 query（搜索关键词）")

        query = query.strip()
        if not query:
            raise ToolInputError("query 不能为空")

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
                    "intentName": "SearchFile",
                    "bundleName": "com.huawei.hmos.aidispatchservice",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {
                        "query": query,
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
        outputs = await execute_device_command("SearchFile", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"搜索文件失败: {error_msg} (错误代码: {code})")

        # 提取结果
        result = outputs.get("result", {})
        files = result.get("items", []) if isinstance(result, dict) else []

        logger.info(f"[FILE_TOOL] Found {len(files)} files")

        return format_success_response(
            {"files": files, "count": len(files)},
            f"搜索到 {len(files)} 个文件"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[FILE_TOOL] Failed to search files: {e}")
        raise RuntimeError(f"搜索文件失败: {str(e)}") from e


@tool(
    name="upload_files",
    description="""将手机本地文件上传并获取可公网访问的 URL。

前置工具调用：此工具使用前必须先调用 search_files 工具获取文件的 uri

工具参数说明：
a. 入参中的fileInfos数组，每个元素必须包含mediaUri字段（对应于search_file工具返回结果中的uri），必须与search_file结果中对应的uri完全保持一致，不要自行修改。
b. fileInfos中的timeout字段是可选的，表示上传文件超时时间，单位是毫秒，默认是20000（20秒）。
c. fileInfos 是文件在手机本地的信息数组（从 search_file 工具响应中获取）。限制：每次最多支持传入 5 条文件信息。

注意：
- 操作超时时间为60秒，请勿重复调用此工具，如果超时或失败，最多重试一次
- 此工具返回的文件链接为用户公网可访问的链接，如果需要对文件进行额外的操作，需要先根据返回的url下载文件，然后进行下一步处理
""",
)
async def upload_files(file_infos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """上传文件.

    Args:
        file_infos: 文件信息数组，每个元素包含mediaUri（必需）和timeout（可选，默认20000）

    Returns:
        包含上传URL的响应字典
    """
    try:
        logger.info(f"[FILE_TOOL] Uploading files - file_infos count: {len(file_infos)}")

        # 验证参数
        if not file_infos or not isinstance(file_infos, list):
            raise ToolInputError("file_infos 必须是包含文件信息的数组")

        if len(file_infos) > 5:
            raise ToolInputError(f"每次最多支持上传 5 个文件，当前提供了 {len(file_infos)} 个")

        # 验证每个文件信息
        for i, file_info in enumerate(file_infos):
            if not isinstance(file_info, dict):
                raise ToolInputError(f"file_infos[{i}] 必须是对象")
            if not file_info.get("mediaUri") or not isinstance(file_info["mediaUri"], str):
                raise ToolInputError(f"file_infos[{i}] 必须包含有效的 mediaUri 字符串")
            # 设置默认超时
            if not file_info.get("timeout"):
                file_info["timeout"] = "20000"

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
                    "intentName": "FileUploadForClaw",
                    "bundleName": "com.huawei.hmos.vassistant",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {"fileInfos": file_infos},
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
        outputs = await execute_device_command("FileUploadForClaw", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"获取文件URL失败: {error_msg} (错误代码: {code})")

        # 提取结果并解码URL
        result = outputs.get("result", {})
        file_urls = result.get("fileUrls", []) if isinstance(result, dict) else []

        # 解码 Unicode 转义序列
        decoded_urls = []
        for url in file_urls:
            if isinstance(url, str):
                decoded_url = url.replace("\\u003d", "=").replace("\\u0026", "&")
                decoded_urls.append(decoded_url)

        logger.info(f"[FILE_TOOL] Uploaded {len(decoded_urls)} files")

        return format_success_response(
            {
                "fileUrls": decoded_urls,
                "count": len(decoded_urls),
                "message": f"成功获取 {len(decoded_urls)} 个文件的公网访问 URL"
            },
            f"成功上传 {len(decoded_urls)} 个文件"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[FILE_TOOL] Failed to upload files: {e}")
        raise RuntimeError(f"上传文件失败: {str(e)}") from e


@tool(
    name="send_file_to_user",
    description="""将手机上的文件发送给用户（通过当前会话渠道）。

前置条件：
- 必须先调用 search_files 工具获取文件的 fileUri
- 文件会被发送到当前会话中

注意：
- 操作超时时间为60秒，请勿重复调用
""",
)
async def send_file_to_user(file_uri: str, file_name: Optional[str] = None) -> Dict[str, Any]:
    """发送文件给用户.

    Args:
        file_uri: 文件URI，必填
        file_name: 文件名（可选，用于显示）

    Returns:
        包含发送结果的响应字典
    """
    try:
        logger.info(f"[FILE_TOOL] Sending file to user - file_uri: {file_uri}")

        # 验证参数
        if not file_uri or not isinstance(file_uri, str):
            raise ToolInputError("缺少必填参数 file_uri（文件URI）")

        if not file_uri.startswith("file://"):
            raise ToolInputError("file_uri 必须以 file:// 开头")

        # 构建参数
        intent_param = {"fileUri": file_uri}
        if file_name:
            intent_param["fileName"] = file_name

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
                    "intentName": "SendFileToUser",
                    "bundleName": "com.huawei.hmos.vassistant",
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
        outputs = await execute_device_command("SendFileToUser", command)

        # 检查错误码
        code = outputs.get("code")
        if code is not None and code != 0:
            error_msg = outputs.get("errorMsg") or outputs.get("errMsg") or "未知错误"
            raise RuntimeError(f"发送文件失败: {error_msg} (错误代码: {code})")

        result = outputs.get("result", {}) if isinstance(outputs, dict) else {}

        logger.info("[FILE_TOOL] File sent successfully")

        return format_success_response(
            {"file_uri": file_uri, "file_name": file_name or "unknown", "result": result},
            f"文件已发送给用户"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[FILE_TOOL] Failed to send file: {e}")
        raise RuntimeError(f"发送文件失败: {str(e)}") from e
