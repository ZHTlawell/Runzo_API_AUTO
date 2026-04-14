"""
SSE（Server-Sent Events）流式响应解析器

功能说明:
    解析 text/event-stream 格式的流式响应，用于 AI 对话接口。

    SSE 事件格式:
        event:{event_type}
        data:{event_data}
        （空行分隔事件）

    stream-chat 接口的事件类型:
        - requestMsgId:  请求消息ID（即 chatId，用于 change-plan）
        - intent:        意图类型（chat=普通问答, GEN_PLAN=生成计划）
        - renderType:    渲染类型（html=HTML卡片, message=纯文本）
        - html:          HTML 内容（AI 回复的富文本卡片）
        - message:       纯文本消息内容
        - responseMsgId: 响应消息ID
        - done:          结束标记，data=[DONE]

使用示例:
    response = requests.post(url, json=payload, stream=True)
    result = SSEParser.parse(response)
    print(result.chat_id)       # requestMsgId
    print(result.intent)        # chat / GEN_PLAN
    print(result.is_done)       # True
"""
from __future__ import annotations

from dataclasses import dataclass, field

from requests import Response

from common.logger import log


@dataclass
class SSEResult:
    """
    SSE 流式响应解析结果

    Attributes:
        chat_id: 对话ID（从 requestMsgId 事件提取）
        intent: 意图类型（chat / GEN_PLAN）
        render_type: 渲染类型（html / message）
        content: 消息内容（html 或 message 事件的完整内容）
        response_msg_id: 响应消息ID
        is_done: 是否收到 done 事件
        events: 所有事件的原始列表 [(event_type, event_data), ...]
        raw_lines: 原始行列表
    """
    chat_id: str = ""
    intent: str = ""
    render_type: str = ""
    content: str = ""
    response_msg_id: str = ""
    is_done: bool = False
    events: list[tuple[str, str]] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


class SSEParser:
    """SSE 流式响应解析器"""

    @staticmethod
    def parse(response: Response, timeout_lines: int = 500) -> SSEResult:
        """
        解析 SSE 流式响应

        逐行读取 SSE 事件流，提取关键字段。
        HTML 内容可能跨多行（被 SSE 分成多个 data: 行），会自动拼接。

        Args:
            response: requests Response 对象（需要 stream=True）
            timeout_lines: 最大读取行数（防止无限流）

        Returns:
            SSEResult 解析结果
        """
        result = SSEResult()
        current_event = ""
        current_data_lines: list[str] = []
        line_count = 0

        for line in response.iter_lines(decode_unicode=True):
            result.raw_lines.append(line if line else "")
            line_count += 1

            if line_count > timeout_lines:
                log.warning(f"SSE 解析超过 {timeout_lines} 行，停止读取")
                break

            if line.startswith("event:"):
                # 如果有上一个事件的 data 还没处理，先处理
                if current_event and current_data_lines:
                    full_data = "\n".join(current_data_lines)
                    _process_event(result, current_event, full_data)
                    current_data_lines = []

                current_event = line[len("event:"):].strip()

            elif line.startswith("data:"):
                data_content = line[len("data:"):]
                current_data_lines.append(data_content)

            elif line == "":
                # 空行 = 事件边界
                if current_event and current_data_lines:
                    full_data = "\n".join(current_data_lines)
                    _process_event(result, current_event, full_data)
                    current_event = ""
                    current_data_lines = []

        # 处理最后一个事件（如果没有尾部空行）
        if current_event and current_data_lines:
            full_data = "\n".join(current_data_lines)
            _process_event(result, current_event, full_data)

        log.info(
            f"SSE 解析完成: chat_id={result.chat_id}, "
            f"intent={result.intent}, render_type={result.render_type}, "
            f"is_done={result.is_done}, events={len(result.events)}"
        )
        return result


def _process_event(result: SSEResult, event_type: str, data: str):
    """处理单个 SSE 事件"""
    result.events.append((event_type, data))

    if event_type == "requestMsgId":
        result.chat_id = data.strip()
    elif event_type == "intent":
        result.intent = data.strip()
    elif event_type == "renderType":
        result.render_type = data.strip()
    elif event_type == "html":
        result.content = data
    elif event_type == "message":
        # message 可能是流式逐字输出，需要拼接
        result.content += data
    elif event_type == "responseMsgId":
        result.response_msg_id = data.strip()
    elif event_type == "done":
        result.is_done = True
