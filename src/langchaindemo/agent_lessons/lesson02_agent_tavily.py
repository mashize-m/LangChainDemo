"""
Agent Lesson 02: Agent 自动执行工具调用 (Tavily 搜索引擎)

说明：
此代码保留了教程示例的核心逻辑，并适配 LangChain 1.x 最新规范。
使用官方推荐的 langchain.agents.create_agent 替代已弃用的 create_react_agent。
"""

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
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个会调用工具的助手,帮助用户解答问题"
    )

    # 4. 调用智能体
    # 智能体会自己决定是否调用 Tavily 引擎，联网获取数据并生成答案
    resp = agent.invoke(
        {
            "messages": [{"role": "user", "content": "今天北京的天气怎么样？"}]
        }
    )

    # 5. 打印结果
    print("\n--- 原始完整返回结果 ---")
    print(resp)

    print("\n--- 最终回答 ---")
    print(resp['messages'][-1].content)


if __name__ == "__main__":
    main()