# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Photo tools - 相册工具.

包含：
- search_photos: 搜索照片
- upload_photos: 上传照片
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
    name="search_photo_gallery",
    description="""搜索用户手机图库中的照片。

根据图像描述语料检索匹配的照片，返回照片在手机本地的 mediaUri 以及 thumbnailUri。
注意：返回的 mediaUri 和 thumbnailUri 是本地路径，无法直接下载或访问。如果需要下载、查看、使用或展示照片，请使用 upload_photos 工具将 mediaUri 或 thumbnailUri 转换为可访问的公网 URL。
- mediaUri 代表手机相册中的图片原图路径，图片大小比较大，清晰度比较高
- thumbnailUri 代表手机相册中的图片缩略图路径，图片大小比较小，清晰度适中，建议在 upload_photos 工具的入参中优先使用此路径，不容易引起上传超时等问题

参数说明：
- query: 图像描述语料，用于检索匹配的照片（例如：'小狗的照片'、'带有键盘的图片'等）

注意：
- 只有当用户明确表达从手机相册搜索或者从图库搜索时才执行此工具
- 操作超时时间为60秒，请勿重复调用，如果超时或失败，最多重试一次
""",
)
async def search_photo_gallery(
    query: str,
) -> Dict[str, Any]:
    """搜索照片.

    Args:
        query: 图像描述语料，用于检索匹配的照片

    Returns:
        包含照片列表的响应字典
    """
    try:
        logger.info(f"[PHOTO_TOOL] Searching photos - query: {query}")

        # 验证参数
        if not query:
            raise ToolInputError("缺少必填参数 query（搜索关键词）")

        # 构建命令 - 与 xy_channel search-photo-gallery-tool.ts 保持一致
        command = {
            "header": {
                "namespace": "Common",
                "name": "Action",
            },
            "payload": {
                "cardParam": {},
                "executeParam": {
                    "executeMode": "background",
                    "intentName": "SearchPhotoVideo",  # 注意：xy_channel 使用 SearchPhotoVideo
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
        outputs = await execute_device_command("SearchPhotoVideo", command)

        # 提取结果（与 xy_channel 一致）
        result = outputs.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []

        logger.info(f"[PHOTO_TOOL] Found {len(items)} photos")

        return format_success_response(
            {
                "items": items,
                "count": len(items),
                "message": f"找到 {len(items)} 张照片。注意：mediaUri 和 thumbnailUri 是本地路径，无法直接访问。"
                           f"如需下载或查看，请使用 upload_photos 工具。"
            },
            f"搜索到 {len(items)} 张照片"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[PHOTO_TOOL] Failed to search photos: {e}")
        raise RuntimeError(f"搜索照片失败: {str(e)}") from e


@tool(
    name="upload_photo",
    description="""将手机本地文件回传并获取可公网访问的 URL。

前置工具调用：此工具使用前必须先调用 search_photo_gallery 工具获取照片的 mediaUri 或者 thumbnailUri
工具参数说明：
- 入参中的 mediaUris 中的 mediaUri 必须与 search_photo_gallery 结果中对应的 mediaUri 或者 thumbnailUri 完全保持一致，不要自行修改，必须是 file:// 开头的路径
- 优先使用 search_photo_gallery 结果中的 thumbnailUri 作为入参，thumbnailUri 是缩略图，清晰度与文件大小都非常合适展示给用户，如果 thumbnailUri 不存在或者用户要求使用原图，则使用 search_photo_gallery 结果中对应的 mediaUri
- mediaUris 是照片在手机本地的 URI 数组（从 search_photo_gallery 工具响应中获取）。限制：每次最多支持传入 3 条 mediaUri

注意：
- 操作超时时间为60秒，请勿重复调用，如果超时或失败，最多重试一次
- 此工具返回的图片链接为用户公网可访问的链接，如果需要后续操作需要下载到本地，如果需要返回给用户查看则直接以图片 markdown 的形式返回给用户
""",
)
async def upload_photo(media_uris: List[str]) -> Dict[str, Any]:
    """上传照片.

    Args:
        media_uris: 照片媒体URI列表，每次最多3个（建议优先使用 thumbnailUri）

    Returns:
        包含上传URL的响应字典
    """
    try:
        logger.info(f"[PHOTO_TOOL] Uploading photos - media_uris count: {len(media_uris)}")

        # ===== 参数规范化：兼容数组和 JSON 字符串 =====
        normalized_uris: List[str]

        if not media_uris:
            raise ToolInputError("缺少必填参数 media_uris")

        # 情况1: 已经是数组
        if isinstance(media_uris, list):
            normalized_uris = media_uris
        # 情况2: 是字符串，尝试解析为 JSON 数组
        elif isinstance(media_uris, str):
            try:
                parsed = json.loads(media_uris)
                if isinstance(parsed, list):
                    normalized_uris = parsed
                else:
                    raise ToolInputError("media_uris 必须是数组或 JSON 数组字符串")
            except json.JSONDecodeError as e:
                raise ToolInputError(f"media_uris JSON 解析失败: {e}") from e
        else:
            raise ToolInputError(f"media_uris 类型错误: {type(media_uris)}")

        if len(normalized_uris) == 0:
            raise ToolInputError("media_uris 数组不能为空")

        # 限制最多3条
        if len(normalized_uris) > 3:
            raise ToolInputError(f"每次最多支持上传 3 张照片，当前提供了 {len(normalized_uris)} 张")

        # 验证URI格式
        for uri in normalized_uris:
            if not isinstance(uri, str) or not uri.startswith("file://"):
                raise ToolInputError(f"无效的 mediaUri: {uri}，必须以 file:// 开头")

        logger.info(f"[PHOTO_TOOL] 验证通过，准备上传 {len(normalized_uris)} 张照片")

        # 构建参数
        image_infos = [{"mediaUri": uri} for uri in normalized_uris]

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
                    "intentName": "ImageUploadForClaw",
                    "bundleName": "com.huawei.hmos.vassistant",
                    "needUnlock": True,
                    "actionResponse": True,
                    "appType": "OHOS_APP",
                    "timeOut": 5,
                    "intentParam": {"imageInfos": image_infos},
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
        outputs = await execute_device_command("ImageUploadForClaw", command)

        # 提取结果
        result = outputs.get("result", {})
        image_urls = result.get("imageUrls", []) if isinstance(result, dict) else []

        # 解码 URL 中的 Unicode 转义序列（如 \u003d -> =, \u0026 -> &）
        decoded_urls = []
        for url in image_urls:
            decoded_url = url.replace("\\u003d", "=").replace("\\u0026", "&")
            decoded_urls.append(decoded_url)
            logger.info(f"[PHOTO_TOOL] Decoded URL: {url} -> {decoded_url}")

        logger.info(f"[PHOTO_TOOL] Uploaded {len(decoded_urls)} photos")

        return format_success_response(
            {
                "imageUrls": decoded_urls,
                "count": len(decoded_urls),
                "message": f"成功获取 {len(decoded_urls)} 张照片的公网访问 URL"
            },
            f"成功上传 {len(decoded_urls)} 张照片"
        )

    except ToolInputError:
        raise
    except Exception as e:
        logger.error(f"[PHOTO_TOOL] Failed to upload photos: {e}")
        raise RuntimeError(f"上传照片失败: {str(e)}") from e
