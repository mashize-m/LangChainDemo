# pip install langchain_mcp_adapters
# pip install --upgrade mcp langchain-mcp-adapters
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
import asyncio

# 导入你本地项目的配置
from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

client = MultiServerMCPClient(
    {
        "mcp_tool_12306": {
          "transport": "streamable_http", #必须将  type修改为transport
          "url": "https://mcp.api-inference.modelscope.net/07acf3302eb144/mcp"
        }
        # "amap-maps": {
        # "transport": "streamable_http",
        # "url": "https://mcp.api-inference.modelscope.net/14db9c03451e47/mcp"
        # }
    }
)


def print_message(message):
    from langchain.messages import AIMessage, HumanMessage, ToolMessage
    if isinstance(message, AIMessage):
        print("AI 回复：", message.content)
        print("AI 决定调用工具", message.tool_calls)
    elif isinstance(message, HumanMessage):
        print("用户输入：", message.content)
    elif isinstance(message, ToolMessage):
        print("工具调用：", message.content)
    else:
        print("未知消息类型")


async def main():
    tools = await client.get_tools()
    print(tools)

    def handle_tool_error(error) -> str:
        return f"Tool execution failed: {str(error)}"

    # 配置工具错误所对应的处理方式，避免工具调用错误导致整个 agent执行过程退出
    for tool in tools:
        tool.handle_tool_error = handle_tool_error

    # 2. 初始化大模型
    print("2. 正在初始化大模型...")
    llm = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
        temperature=0
    )

    agent = create_agent(
        llm,
        tools,
    )

    while True:
        user_input = input(">")
        if user_input == "exit":
            break
        res = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]},config={"configurable": {"thread_id": "1"}})
        print(res['messages'][-1].content, end="\n\n")
        for message in res["messages"]:
            print_message(message)
            print("\n")
        print("\n")



"""
ValueError: Configuration error: Missing 'transport' key in server configuration. Each server must include 'transport' with one of: 'stdio', 'sse', 'websocket', 'http'. Please refer to the langchain-mcp-adapters documentation for more details.

"""

if __name__ == "__main__":
    # MCP Client 必须运行在异步环境中
    asyncio.run(main())