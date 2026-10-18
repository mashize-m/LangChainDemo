"""
Agent Lesson 01: 通过 LangChain 定义工具 (Tools)

流程说明：
1. 使用 @tool 装饰器定义一个函数，作为大模型可调用的工具。
2. 将工具绑定到大模型（bind_tools）。
3. 向大模型发送用户请求。
4. 大模型分析请求，返回一个包含【工具调用请求】的 AIMessage。
5. 我们在本地执行该工具，拿到真实数据。
6. 将工具的执行结果封装成 ToolMessage，发回给大模型。
7. 大模型结合工具返回的数据，生成最终的自然语言回答。
"""

from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain.chat_models import init_chat_model

# 复用项目原有的配置
from langchaindemo.config import OPENAI_MODEL


# ================= 1. 定义工具 =================
@tool
def get_weather(city: str, date: str) -> str:
    """
    获取指定城市在指定日期的天气情况。

    Args:
        city: 城市名称（如：北京、上海）
        date: 日期，格式为 YYYY-MM-DD
    """
    # 实际业务中，这里会调用第三方天气 API，现在用 Mock 数据模拟
    return f"{city} 在 {date} 天气多云，有下雨的可能性，出门请带伞。"


# ================= 2. 主流程 =================
def main():
    print("1. 正在初始化大模型...")
    # 使用 init_chat_model，它会自动读取 config 中配置的 API Key 和 Base URL
    llm = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
        temperature=0.0  # 工具调用场景需要严谨，温度调低
    )

    # 将定义好的工具绑定到大模型
    llm_with_tools = llm.bind_tools([get_weather])

    # 用户提问
    user_query = "北京 2026-09-25 的天气怎么样？"
    print(f"\n👤 用户提问: {user_query}")

    message_list = [HumanMessage(content=user_query)]

    # ================= 3. 第一轮调用：大模型决定是否使用工具 =================
    print("\n2. 向大模型发起首次请求...")
    ai_msg = llm_with_tools.invoke(message_list)
    message_list.append(ai_msg)

    # 检查大模型是否真的决定调用工具
    if not ai_msg.tool_calls:
        print("\n🤖 大模型直接回复（未调用工具）：")
        print(ai_msg.content)
        return

    # ================= 4. 解析并执行工具 =================
    print(f"\n3. 大模型请求调用工具，共 {len(ai_msg.tool_calls)} 个请求。")

    for tool_call in ai_msg.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        print(f"   -> 准备执行工具: {tool_name}")
        print(f"   -> 提取到的参数: {tool_args}")

        # 手动在本地执行对应的工具
        if tool_name == "get_weather":
            # 使用 .invoke() 执行工具
            tool_result = get_weather.invoke(tool_args)
            print(f"   -> 工具执行结果: {tool_result}")

            # ================= 5. 封装结果并返回给大模型 =================
            # ToolMessage 必须携带对应的 tool_call_id，大模型才知道这是哪次请求的结果
            tool_msg = ToolMessage(
                tool_call_id=tool_id,
                content=tool_result
            )
            message_list.append(tool_msg)

    # ================= 6. 第二轮调用：大模型基于结果生成最终回答 =================
    print("\n4. 将工具执行结果发回给大模型，等待最终回答...")
    final_msg = llm_with_tools.invoke(message_list)

    print("\n" + "=" * 20 + " 最终回答 " + "=" * 20)
    print(final_msg.content)
    print("=" * 50)


if __name__ == "__main__":
    main()