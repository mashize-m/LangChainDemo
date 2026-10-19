"""
基于LangChain的create_agent实现checkpointer机制

    短期记忆： InMemorySaver()

    针对于不同的会话进行测试。

    需要更改：thread_id

    result3 = app.invoke(
        input={"query": '问题3'},  # 新会话的初始输入
        config={"configurable": {"thread_id": new_thread_id}}  # 新的 thread_id
    )


"""


"""
LangGraph 状态存储示例：使用 Checkpointer 保持会话上下文
"""
import operator
from typing import TypedDict, List, Annotated

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph


# 1. 定义图状态
class AgentState(TypedDict):
    query: str  # 用户问题
    current_context: Annotated[List[str], operator.add]  # 当前上下文摘要（用于演示）


# 2. 定义节点函数
def echo_node(state: AgentState):
    # 获取用户问题
    query = state["query"]

    # 更新上下文摘要（简化模拟）
    new_context = f"最近一次交流: {query}"

    return {
        "current_context": [new_context]
    }


# 3. 构建图
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("echo", echo_node)
    graph.add_edge(START, "echo")
    graph.add_edge("echo", END)  # 直接结束
    return graph


# 4. 主函数
def demo_langgraph():

    # 1. 创建 Checkpointer 实例
    checkpointer = InMemorySaver()  # 选择内存存储

    # 2. 构建图
    graph = build_graph()

    # 3. 编译图时传入 Checkpointer
    app = graph.compile(checkpointer=checkpointer)

    # 4. 用户第一次调用
    print("--- 第一次调用 ---")
    result1 = app.invoke(
        input={"query": "问题1"},
        config={"configurable": {"thread_id": "user_session1"}}
    )
    print("第一次当前上下文:", result1["current_context"])

    # 5. 用户在同一个会话中第二次调用
    print("\n--- 第二次调用 (同一会话) ---")
    # 不需要再次传入初始 messages，会自动从 checkpointer 加载状态
    result2 = app.invoke(
        input={"query": "问题2"},
        config={"configurable": {"thread_id": "user_session1"}}  # 同一个 thread_id
    )


    print("第二次当前上下文:", result2["current_context"])

    # 6. 启动一个新会话
    print("\n--- 第三次调用 (新会话) ---")
    new_thread_id = "user_session2"  # 新的 thread_id
    result3 = app.invoke(
        input={"query": '问题3'},  # 新会话的初始输入
        config={"configurable": {"thread_id": new_thread_id}}  # 新的 thread_id
    )
    print("新会话当前上下文:", result3["current_context"])


if __name__ == "__main__":
    demo_langgraph()