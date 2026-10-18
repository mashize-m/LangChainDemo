# ===== 1. 加载.env =====
import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

# 导入你本地项目的配置
from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

# ===== 2. 定义工具 =====
@tool
def get_weather(city: str) -> str:
    """
    查询天气
    :param city: 要查询的城市
    :return: 查询结果
    """
    return f"{city}的天气晴朗，气温25度。"

@tool
def transfer_money(amount: int, to_account: str) -> str:
    """
    转账操作（敏感操作，需要审核）
    :param amount: 转账金额（元）
    :param to_account: 收款账户名称
    :return: 转账结果
    """
    return f"成功转账 {amount} 元给 {to_account}。"


# ===== 3. 配置中间件 =====
hitl_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        "transfer_money": True,    # 转账需要审核
        "get_weather": False,      # 查天气不需要
    }
)


# ===== 4. 创建Agent =====
llm = init_chat_model(
    model=OPENAI_MODEL,
    model_provider="openai",
    temperature=0
)

# 必须配合历史记忆使用
checkpointer = InMemorySaver()
agent = create_agent(
    model=llm,
    tools=[get_weather, transfer_money],
    middleware=[hitl_middleware],
    checkpointer=checkpointer
)



async def run_demo():
    # ===== 5. 问题1 =====
    messages1 = [{"role": "user", "content": "深圳天气如何"}, ]
    res1 = agent.invoke(
        input={"messages": messages1},
        config={"configurable": {"thread_id": "thread-1"}}
    )
    print(res1)

    # ===== 6. 问题2 =====
    # messages2 = [{"role": "user", "content": "请给王嘉尔转账1000000"}, ]
    messages2 = [{"role": "user", "content": "请同时给张三转账100万，给李四转账200万，给王五转账300万"}, ]
    res2 = agent.invoke(
        input={"messages": messages2},
        config={"configurable": {"thread_id": "thread-2"}}
    )
    print(res2)

    if "__interrupt__" in res2:

        interrupt_value = res2["__interrupt__"][0].value
        print("需要审核的敏感操作")

        decision = "reject" # reject or approve
        action_requests = interrupt_value.get("action_requests")

        # 批量同意
        decisions = [{"type": decision} for _ in action_requests]
        result = agent.invoke(
            Command(resume={"decisions": decisions}),
            config={"configurable": {"thread_id": "thread-2"}}
        )


        for msg in result.get("messages"):
            # 判断消息类型是否为ai消息，并且没有tool_calls属性
            if hasattr(msg, "type") and msg.type == "ai" and not getattr(msg, "tool_calls", None):
                print(f"[Agent]: {msg.content}")


if __name__ == '__main__':
    asyncio.run(run_demo())