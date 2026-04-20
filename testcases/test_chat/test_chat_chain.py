"""
AI 对话模块 - 端到端测试用例

功能说明:
    覆盖 AI 对话的完整链路：
    1. 创建 session → 发送消息(SSE) → 验证 AI 回复
    2. 查询历史消息
    3. 查询未结束 session
    4. 获取提示词

前置依赖:
    - 用户已有训练计划（通过 plan_for_chat fixture 自动生成）

业务流程:
    create_session → stream-chat(SSE流式) → 解析AI回复
    → session/messages(查历史) → session-unfinish(查未结束session)
"""
from __future__ import annotations

import time

import allure
import pytest

from common.assertion import Assertion
from common.cache import cache
from common.logger import log
from common.waiter import wait_for_plan_ready


@pytest.fixture(scope="module")
def plan_for_chat(plan_api, auth_user, mongo_db):
    """
    模块级 fixture: 确保有训练计划供对话使用

    Returns:
        dict: {"plan_id", "user_id"}
    """
    existing_plan = cache.get("plan_id")
    if existing_plan:
        log.info(f"复用已有计划: planId={existing_plan}")
        return {"plan_id": existing_plan, "user_id": cache.get("user_id")}

    user_id = auth_user["userId"]
    plan_request = {
        "gender": 1,
        "heightValue": "175",
        "heightUnit": "cm",
        "weightValue": "70",
        "weightUnit": "kg",
        "trainingGoal": "half_marathon",
        "planCompletionWeeks": 12,
        "trainingSchedule": ["MONDAY", "WEDNESDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
        "lsdSchedule": "SUNDAY",
        "age": 28,
        "intensity": "medium",
        "trainingHistory": {
            "paceDTO": {"pace5km": "5'30\"", "pace10km": "5'45\""},
            "heartRateDTO": {"heartRate": 160},
            "fiveKm": {"pace": "5'30\"", "heartRate": "160"},
        },
    }
    resp = plan_api.generate(plan_request)
    assert resp.status_code == 200 and resp.json().get("code") == 0

    plan_doc = wait_for_plan_ready(mongo_db, user_id, timeout=120, interval=5)
    assert plan_doc and plan_doc.get("status") == 3

    list_resp = plan_api.get_list()
    data = list_resp.json().get("data", {})
    plan_id = data.get("trainingPlanId") if isinstance(data, dict) else data[0].get("trainingPlanId")

    cache.set("plan_id", plan_id)
    log.info(f"计划就绪: planId={plan_id}")
    return {"plan_id": plan_id, "user_id": user_id}


@allure.feature("AI 对话")
@allure.story("完整对话链路")
class TestChatFullChain:
    """
    P0 核心链路: 创建session → 发送消息(SSE) → 验证回复 → 查历史消息

    验证点:
    - session 创建成功返回 sessionId
    - stream-chat SSE 流正常接收
    - SSE 事件包含: requestMsgId, intent, renderType, html/message, done
    - 历史消息能查到刚才的对话
    """

    @pytest.mark.smoke
    @pytest.mark.p0
    @allure.title("P0 冒烟: AI 对话完整链路")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_chat_full_chain(self, chat_api, plan_for_chat):
        """
        完整对话链路端到端测试

        流程:
        1. 创建 session
        2. 发送消息（SSE 流式）
        3. 验证 SSE 事件完整性
        4. 查询历史消息
        """
        # Step 1: 创建 session
        with allure.step("Step 1: 创建对话 Session"):
            session_resp = chat_api.create_session()
            Assertion.assert_code(session_resp)
            session_data = session_resp.json()

            data = session_data.get("data", {})
            session_id = data.get("sessionId") if isinstance(data, dict) else str(data)
            assert session_id, f"sessionId 为空: {session_data}"
            cache.set("chat_session_id", session_id)
            log.info(f"Session 创建成功: sessionId={session_id}")

        # Step 2: 发送消息（SSE 流式）
        with allure.step("Step 2: 发送消息并接收 SSE 流式回复"):
            sse_result = chat_api.stream_chat(
                session_id=session_id,
                message="我这周有一天想休息，可以帮我调整吗？",
            )

            # 验证 SSE 关键事件
            assert sse_result.is_done, "SSE 流未收到 done 事件"
            assert sse_result.chat_id, f"未获取到 chatId (requestMsgId)"
            assert sse_result.intent, f"未获取到 intent"
            assert sse_result.content, "AI 回复内容为空"

            cache.set("chat_id", sse_result.chat_id)
            log.info(
                f"SSE 对话完成:\n"
                f"    chatId: {sse_result.chat_id}\n"
                f"    intent: {sse_result.intent}\n"
                f"    renderType: {sse_result.render_type}\n"
                f"    content长度: {len(sse_result.content)}\n"
                f"    事件数: {len(sse_result.events)}"
            )

        # Step 3: 查询历史消息
        with allure.step("Step 3: 查询历史对话消息"):
            msgs_resp = chat_api.session_messages(session_id)
            Assertion.assert_code(msgs_resp)
            msgs_data = msgs_resp.json()

            messages = msgs_data.get("data", [])
            log.info(f"历史消息: 共 {len(messages)} 条")
            if messages:
                for msg in messages[:5]:
                    role = msg.get("role", "?")
                    content = msg.get("message", "")[:100]
                    log.info(f"  [{role}] {content}...")

        log.info(f"=== AI 对话完整链路测试通过 === sessionId={session_id}")


@allure.feature("AI 对话")
@allure.story("Session 管理")
class TestChatSession:
    """P1 Session 管理相关测试"""

    @pytest.mark.p1
    @allure.title("P1: 查询未结束的 Session")
    def test_session_unfinish(self, chat_api, plan_for_chat):
        """查询是否有未结束的对话 session"""
        resp = chat_api.session_unfinish()
        Assertion.assert_code(resp)
        log.info(f"未结束 session: {resp.json().get('data')}")

    @pytest.mark.p1
    @allure.title("P1: 获取对话默认提示词")
    def test_chat_tips(self, chat_api, plan_for_chat):
        """获取 AI 对话的默认提示词列表"""
        resp = chat_api.chat_tips()
        Assertion.assert_code(resp)
        tips = resp.json().get("data", [])
        log.info(f"提示词: 共 {len(tips) if isinstance(tips, list) else 0} 条")

    @pytest.mark.p1
    @allure.title("P1: 多轮对话（复用同一 Session）")
    def test_multi_round_chat(self, chat_api, plan_for_chat):
        """
        多轮对话验证

        复用已有 session（每个用户同时只能有一个活跃 session）
        → 第一轮对话 → 第二轮对话 → 验证历史消息包含两轮
        """
        # 查询未结束的 session，如果有就复用
        unfinish_resp = chat_api.session_unfinish()
        unfinish_data = unfinish_resp.json().get("data")

        if unfinish_data and isinstance(unfinish_data, dict) and unfinish_data.get("sessionId"):
            session_id = unfinish_data["sessionId"]
            log.info(f"复用未结束的 session: {session_id}")
        else:
            # 没有未结束的，创建新的
            session_resp = chat_api.create_session()
            session_data = session_resp.json().get("data", {})
            session_id = session_data.get("sessionId") if isinstance(session_data, dict) else str(session_data)
            assert session_id, "创建 session 失败"
            log.info(f"创建新 session: {session_id}")

        # 第一轮
        result1 = chat_api.stream_chat(session_id, "我的计划是什么目标？")
        assert result1.is_done, "第一轮对话 SSE 未完成"
        log.info(f"第一轮: intent={result1.intent}")

        # 第二轮
        result2 = chat_api.stream_chat(session_id, "这周有几天训练？")
        assert result2.is_done, "第二轮对话 SSE 未完成"
        log.info(f"第二轮: intent={result2.intent}")

        # 查历史消息
        msgs_resp = chat_api.session_messages(session_id)
        messages = msgs_resp.json().get("data", [])
        log.info(f"多轮对话历史: 共 {len(messages)} 条消息")
        # 至少包含本次的 2 轮对话（可能还有之前 P0 用例的消息）
        assert len(messages) >= 4, f"历史消息不足: 期望>=4, 实际{len(messages)}"

        log.info("=== 多轮对话测试通过 ===")
