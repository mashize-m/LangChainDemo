# pip install langchain_mcp_adapters
# pip install --upgrade mcp langchain-mcp-adapters
import asyncio
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

# 导入你本地项目的模型配置
from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

# MCP 服务配置
client = MultiServerMCPClient(
    {
        "mcp_tool_12306": {
            "transport": "streamable_http",  # 如果报错，请改为 sse 或 http
            "url": "https://mcp.api-inference.modelscope.net/07acf3302eb144/mcp"
        }
    }
)


async def main():
    print("1. 正在获取 MCP 工具...")
    tools = await client.get_tools()

    def handle_tool_error(error) -> str:
        return f"Tool execution failed: {str(error)}"

    for tool in tools:
        tool.handle_tool_error = handle_tool_error

    # 2. 初始化大模型
    print("2. 正在初始化大模型...")
    llm = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
        temperature=0
    )

    # 3. 创建记忆存储实例
    memory = InMemorySaver()

    # 4. 获取当前时间，直接注入到 system_prompt 中
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    agent = create_agent(
        model=llm,
        tools=tools,
        checkpointer=memory,  # 关键点：传入 checkpointer
        system_prompt=f"你是一个智能助手。当前时间是 {current_time}。你可以调用工具帮用户查询信息。"
    )

    # 定义同一个会话的 ID
    config = {"configurable": {"thread_id": "user_001"}}

    # ================= 模拟第一次对话 =================
    query_1 = "帮我查一下明天从北京到上海的高铁票"
    print(f"\n👤 用户: {query_1}")
    print("🤖 Agent 正在思考...\n")

    # 使用 ainvoke 获取完整结果（避免刷屏）
    res_1 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query_1}]},
        config=config
    )
    print("=== 第一次回答 ===")
    print(res_1['messages'][-1].content[:300] + "...\n(内容过长已截断)")

    # ================= 模拟第二次对话（测试记忆） =================
    # 注意：这里没有再提“北京”和“上海”，看模型是否记得
    query_2 = "那后天呢？"
    print(f"\n👤 用户: {query_2}")
    print("🤖 Agent 正在思考...\n")

    res_2 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query_2}]},
        config=config  # 关键点：使用相同的 thread_id
    )
    print("=== 第二次回答 ===")
    print(res_2['messages'][-1].content[:300] + "...\n(内容过长已截断)")


if __name__ == "__main__":
    asyncio.run(main())