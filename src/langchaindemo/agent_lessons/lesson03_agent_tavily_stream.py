"""
Agent Lesson 03: Agent 流式输出 (Tavily 搜索引擎)

说明：
1. 使用 stream_mode="messages" 实现流式输出（打字机效果）。
2. 通过 metadata["langgraph_node"] 过滤掉底层工具（Tavily）返回的原始 JSON 数据，
   只打印大模型最终生成的文本，让控制台输出保持清爽。
"""
import time
import warnings

# 屏蔽 Tavily 库内部字段重名的无害警告
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_tavily")

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain.agents import create_agent

# 导入你本地项目的配置
from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)


def main():
    # 1. 创建 LLM 模型 (适配本地环境)
    llm = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0
    )

    # 2. 定义工具
    # Tavily 会自动读取你 config 里加载的环境变量 TAVILY_API_KEY
    search = TavilySearch(max_results=5)
    tools = [search]  # 工具列表

    # 3. 创建代理 - 智能体
    # 注意：这里已经统一定义了 system_prompt，调用时不需要再重复传 system 消息
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个会调用工具的助手，帮助用户解答问题"
    )

    print("👤 用户: 今天济南的天气怎么样？\n")
    print("🤖 Agent: ", end="", flush=True)

    # 4. 调用智能体（流式输出）
    for chunk, metadata in agent.stream(
            {
                "messages": [
                    {"role": "user", "content": "今天济南的天气怎么样？"},
                ]
            },
            stream_mode="messages"
    ):
        # 【核心过滤逻辑】
        # 判断当前流式输出的节点是否属于工具节点，如果是，直接跳过
        if metadata.get("langgraph_node") == "tools":
            continue

        # 如果 chunk 的内容不为空，且属于大模型输出，则逐字打印
        if chunk.content:
            print(chunk.content, end="", flush=True)
            # 稍微加个延时，让打字机效果更平滑（可选）
            time.sleep(0.02)

    # 输出结束后换行
    print("\n")


if __name__ == "__main__":
    main()