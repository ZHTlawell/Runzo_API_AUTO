"""
AI 对话模块接口

功能说明:
    封装 turing-runner 服务中 AI 对话相关的 6 个接口。
    用于通过自然语言与 AI 教练对话，实现训练计划调整。

    对话流程:
    1. 创建 session → 获取 sessionId
    2. 发送消息 stream-chat（SSE 流式响应）→ AI 回复
    3. 如果 AI 建议调整计划 → change-plan 接受/拒绝
    4. 查看历史消息 session/messages

    SSE 事件类型:
    - requestMsgId: 对话ID（chatId）
    - intent: 意图（chat=普通问答, GEN_PLAN=生成计划）
    - renderType: 渲染类型（html/message）
    - html/message: 消息内容
    - responseMsgId: 响应消息ID
    - done: 结束标记 [DONE]

前置条件:
    - 用户已有训练计划
    - 计划已开启训练

Session 生命周期:
    - 创建后持续有效，直到计划调整成功
    - 计划调整成功后 session 过期，需重新创建
"""
from __future__ import annotations

import allure

from api.base_api import BaseAPI
from common.logger import log
from common.sse_parser import SSEParser, SSEResult


class ChatAPI(BaseAPI):
    """
    AI 对话相关接口

    方法按对话生命周期排列:
    1. 创建/查询 Session
    2. 发送消息（SSE 流式）
    3. 计划调整决策
    4. 历史消息查询
    5. 提示词
    """

    PREFIX = "/runzo/chat"

    # ========== 1. Session 管理 ==========

    @allure.step("创建新对话 Session")
    def create_session(self):
        """
        创建一个新的 AI 对话 Session

        Returns:
            Response 对象，data 中包含 sessionId
        """
        return self.client.post(f"{self.PREFIX}/session")

    @allure.step("查询有没有未结束的对话 Session")
    def session_unfinish(self):
        """
        查询当前用户是否有未结束的对话 Session

        用于 APP 重新打开时检查上次的对话是否还在。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/session-unfinish")

    # ========== 2. 发送消息（SSE 流式） ==========

    @allure.step("发送对话消息（SSE 流式）")
    def stream_chat(
        self,
        session_id: str,
        message: str,
        force: bool = False,
    ) -> SSEResult:
        """
        发送对话消息，接收 AI 的 SSE 流式响应

        这是 AI 对话的核心接口，返回的是 text/event-stream 流。
        本方法会自动解析 SSE 流并返回结构化的 SSEResult。

        Args:
            session_id: 对话 Session ID
            message: 用户发送的消息内容
            force: 是否跳过软阻断（blocked_soft 场景下用户确认继续时传 True）

        Returns:
            SSEResult 包含:
                - chat_id: 对话ID（用于 change-plan）
                - intent: 意图（chat / GEN_PLAN）
                - render_type: 渲染类型（html / message）
                - content: AI 回复内容
                - is_done: 是否正常结束
        """
        payload = {
            "sessionId": session_id,
            "message": message,
        }
        if force:
            payload["force"] = True

        # 使用 stream=True 接收 SSE 流
        log.info(f">>> SSE POST {self.client.base_url}{self.PREFIX}/stream-chat")
        log.debug(f"    Message: {message}")

        response = self.client.session.request(
            method="POST",
            url=f"{self.client.base_url}{self.PREFIX}/stream-chat",
            json=payload,
            stream=True,
            timeout=60,
        )

        log.info(f"<<< SSE status={response.status_code}, content-type={response.headers.get('content-type')}")

        # 解析 SSE 流
        result = SSEParser.parse(response)

        # Allure 附件
        allure.attach(
            f"chat_id: {result.chat_id}\n"
            f"intent: {result.intent}\n"
            f"render_type: {result.render_type}\n"
            f"is_done: {result.is_done}\n"
            f"events_count: {len(result.events)}\n"
            f"content_length: {len(result.content)}",
            name="SSE 解析结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        return result

    @allure.step("发送对话消息（原始 Response）")
    def stream_chat_raw(
        self,
        session_id: str,
        message: str,
        force: bool = False,
    ):
        """
        发送对话消息，返回原始 Response（不解析 SSE）

        用于需要自定义处理 SSE 流的场景。

        Returns:
            Response 对象（stream=True）
        """
        payload = {
            "sessionId": session_id,
            "message": message,
        }
        if force:
            payload["force"] = True

        return self.client.session.request(
            method="POST",
            url=f"{self.client.base_url}{self.PREFIX}/stream-chat",
            json=payload,
            stream=True,
            timeout=60,
        )

    # ========== 3. 计划调整决策 ==========

    @allure.step("接受或拒绝 AI 计划调整方案")
    def change_plan(self, chat_id: str, accept: bool):
        """
        对 AI 生成的计划调整方案做出决策

        当 stream-chat 的 intent=GEN_PLAN 时，AI 会生成调整方案，
        用户通过此接口接受或拒绝。

        接受后当前 session 过期，需要重新创建。

        Args:
            chat_id: 对话ID（从 stream-chat SSE 的 requestMsgId 事件获取）
            accept: True=接受调整, False=拒绝

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/change-plan",
            json={"chatId": chat_id, "acceptPlan": accept},
        )

    # ========== 4. 历史消息 ==========

    @allure.step("获取 Session 历史对话列表")
    def session_messages(self, session_id: str):
        """
        获取指定 Session 的历史对话消息列表

        Args:
            session_id: 对话 Session ID

        Returns:
            Response 对象，data 为消息列表
        """
        return self.client.get(
            f"{self.PREFIX}/session/messages",
            params={"sessionId": session_id},
        )

    # ========== 5. 提示词 ==========

    @allure.step("获取对话默认提示词")
    def chat_tips(self):
        """
        获取 AI 对话的默认提示词列表

        用于对话界面展示推荐的提问方向。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/chat-tips")
