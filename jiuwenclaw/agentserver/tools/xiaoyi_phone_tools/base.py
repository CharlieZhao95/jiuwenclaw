# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""Base utilities for xiaoyi handset tools.

提供设备侧工具的通用功能：
- 获取 channel 实例
- 发送 command 并等待响应
- 参数验证
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

from jiuwenclaw.utils import logger
from jiuwenclaw.channel.xiaoyi_channel import get_xiaoyi_channel


class ToolInputError(Exception):
    """工具输入参数错误.

    抛出此错误会让框架返回 HTTP 400 而非 500，
    LLM 会将其识别为参数错误而非瞬时故障。
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.status = 400


async def execute_device_command(
    intent_name: str,
    command: Dict[str, Any],
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """执行设备命令并等待响应.

    Args:
        intent_name: Intent 名称，用于匹配响应
        command: Command 数据结构
        timeout: 超时时间（秒）

    Returns:
        包含 content 字段的响应字典

    Raises:
        RuntimeError: 会话不存在或执行失败
        ToolInputError: 参数错误
    """
    logger.info(f"[{intent_name}_TOOL] Starting execution")

    # 获取 XiaoyiChannel 实例
    channel = get_xiaoyi_channel()
    if channel is None:
        logger.error(f"[{intent_name}_TOOL] FAILED: No active session found!")
        raise RuntimeError(
            f"No active XY session found. {intent_name} tool can only be used during an active conversation."
        )

    # 获取会话信息（从 config.yaml，与已验证的 location_tool.py 保持一致）
    session_id = ""
    task_id = ""
    message_id = f"cmd_{int(asyncio.get_event_loop().time() * 1000)}"

    try:
        from jiuwenclaw.config import get_config
        config = get_config()
        xiaoyi_conf = config.get("channels", {}).get("xiaoyi", {})
        session_id = xiaoyi_conf.get("last_session_id", "")
        task_id = xiaoyi_conf.get("last_task_id", "")
    except Exception as e:
        logger.warning(f"[{intent_name}_TOOL] 获取会话信息失败: {e}")

    if not session_id:
        logger.error(f"[{intent_name}_TOOL] FAILED: No valid session found!")
        raise RuntimeError(
            f"No active XY session found. {intent_name} tool can only be used during an active conversation."
        )

    logger.info(f"[{intent_name}_TOOL] Session context found: {session_id}")

    # 创建事件等待结果
    result_event = asyncio.Event()
    result_data: Optional[Dict[str, Any]] = None
    error_result: Optional[Exception] = None

    # 定义 data-event 处理器
    def on_data_event(event):
        nonlocal result_data, error_result
        logger.info(f"[{intent_name}_TOOL] Received data event: intent={event.intent_name}, status={event.status}")
        
        if event.intent_name == intent_name:
            logger.info(f"[{intent_name}_TOOL] Intent name matched! status={event.status}")

            if event.status == "success" and event.outputs:
                result_data = event.outputs
                logger.info(f"[{intent_name}_TOOL] Execution successful, outputs={list(event.outputs.keys())}")
            else:
                error_result = RuntimeError(f"执行失败: {event.status}")
                logger.error(f"[{intent_name}_TOOL] Execution failed: {event.status}")

            result_event.set()
        else:
            logger.debug(f"[{intent_name}_TOOL] Intent name mismatch: expected={intent_name}, got={event.intent_name}")

    # 注册处理器
    channel.register_data_event_handler(intent_name, on_data_event)

    try:
        # 发送命令
        logger.info(f"[{intent_name}_TOOL] Sending command...")
        sent = await channel.send_xiaoyi_phone_tools_command(
            session_id=session_id,
            task_id=task_id or session_id,
            message_id=message_id,
            command=command,
        )

        if not sent:
            raise RuntimeError("发送指令失败，WebSocket 未连接")

        # 等待响应
        logger.info(f"[{intent_name}_TOOL] Waiting for response (timeout: {timeout}s)...")
        await asyncio.wait_for(result_event.wait(), timeout=timeout)

        if error_result:
            raise error_result

        return result_data or {}

    except asyncio.TimeoutError:
        logger.error(f"[{intent_name}_TOOL] Timeout: No response received within {timeout} seconds")

    finally:
        channel.unregister_data_event_handler(intent_name, on_data_event)


def validate_required_params(params: Dict[str, Any], required: list[str]) -> None:
    """验证必填参数.

    Args:
        params: 参数字典
        required: 必填参数名列表

    Raises:
        ToolInputError: 缺少必填参数
    """
    for param_name in required:
        value = params.get(param_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ToolInputError(f"缺少必填参数 {param_name}")


def format_success_response(data: Dict[str, Any], message: str = "") -> Dict[str, Any]:
    """格式化成功响应.

    Args:
        data: 响应数据
        message: 可选的消息

    Returns:
        包含 content 的响应字典
    """
    import json

    response = {"success": True, **data}
    if message:
        response["message"] = message

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(response, ensure_ascii=False),
            }
        ]
    }


def format_error_response(error: str) -> Dict[str, Any]:
    """格式化错误响应.

    Args:
        error: 错误信息

    Returns:
        包含 content 的错误响应字典
    """
    import json

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"success": False, "error": error}, ensure_ascii=False),
            }
        ]
    }
