
"""
LangGraph Reducer函数演示
+ Reducer（默认：覆盖更新）
+ 追加
    messages: Annotated[List[BaseMessage], add_messages]  # 累加  将 HumanMessage, AIMessage, SystemMessage 追加到数组中
    search_results: Annotated[List[str], operator.add]  # 累加  搜索结果列表
    sum_scores: Annotated[float, operator.add]  # 计算总成绩
+ 自定义 累加函数。
    自定义 累加的函数，然后替换之前的 add_messages、operator.add 累加函数即可。例如：
    def custom_add_messages
    def custom_add_search_results

注意：
1、BaseMessage是系统信息、用户信息、工具信息、AI信息，这四类message的父类。
2、串行可以覆盖，但是并行必须累加。

"""
import operator
from typing import List, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, add_messages


# 自定义消息 Reducer：为消息添加图标前缀
def custom_add_messages(
        existing_messages: List[BaseMessage],
        new_messages: List[BaseMessage]
) -> List[BaseMessage]:
    """
    自定义消息追加函数，为不同类型的消息添加图标前缀
    """
    if existing_messages is None:
        existing_messages = []

    icon_map = {
        'system': '🔧 [系统]',
        'human': '👤 [用户]',
        'ai': '🤖 [AI]'
    }

    processed_messages = []
    for msg in new_messages:
        icon = icon_map.get(msg.type)
        # 根据消息类型创建带有前缀的新消息对象
        if isinstance(msg, SystemMessage):
            processed_messages.append(SystemMessage(content=f"{icon} {msg.content}"))
        elif isinstance(msg, HumanMessage):
            processed_messages.append(HumanMessage(content=f"{icon} {msg.content}"))
        elif isinstance(msg, AIMessage):
            processed_messages.append(AIMessage(content=f"{icon} {msg.content}"))
        else:
            processed_messages.append(msg)  # 保持其他类型消息不变

    return existing_messages + processed_messages


# 自定义搜索结果 Reducer：为结果添加序号
def custom_add_search_results(existing_results: List[str], new_results: List[str]) -> List[str]:
    """
    自定义搜索结果追加函数，为每个结果添加序号
    """
    if existing_results is None:
        existing_results = []

    # 计算新序号的起始值
    start_index = len(existing_results) + 1

    # 处理每个结果
    processed_results = []
    for i, result in enumerate(new_results, start=start_index):
        processed_results.append(f"📌 步骤{i}: {result}")

    # 返回更新后的结果列表
    return existing_results + processed_results



# 1. 定义图状态 - 所有字段均未指定reducer，故默认为覆盖
class AgentState(TypedDict):
    query: str

    # 历史消息列表——默认
    # messages: List[BaseMessage]  # 默认 ：覆盖更新
    # search_results: List[str]    # 搜索结果列表

    # 累加模式
    # messages: Annotated[List[BaseMessage], add_messages]  # 累加  将 HumanMessage, AIMessage, SystemMessage 追加到数组中
    # search_results: Annotated[List[str], operator.add]  # 累加  搜索结果列表
    # sum_scores: Annotated[float, operator.add]  # 计算总成绩

    # 自定义
    messages: Annotated[List[BaseMessage], custom_add_messages]  # 历史消息列表  BaseMessage, HumanMessage, AIMessage, SystemMessage
    search_results: Annotated[List[str], custom_add_search_results]  # 搜索结果列表
    sum_scores: Annotated[float, operator.add]  # 计算总成绩


# 2. 节点函数：输入处理
def input_node(state: AgentState):
    query = state["query"]
    new_message = HumanMessage(content=f"用户问题: {query}")

    # 返回新列表，将完全替换掉state["messages"]的旧列表
    return {"messages": [new_message]}

# 3. 节点函数：搜索处理
def search_node(state: AgentState):
    query = state["query"]
    query_result = f"模拟搜索结果：关于'{query}'的相关信息..."
    search_msg = AIMessage(content=f"搜索完成: {query_result}")

    # 返回新列表，将完全替换掉state["search_msg"]和state["query_result"]的旧列表
    return {
        "messages": [search_msg],
        "search_results": [query_result],
        "sum_scores": 1.1
    }

# 4. 节点函数：生成最终回复
def response_node(state: AgentState):
    context = state["search_results"] # 此时search_results只包含上一个节点的单条结果
    query = state["query"]
    final_response = f"基于搜索结果，对问题'{query}'的回答是：{context} "
    ai_response = AIMessage(content=final_response)
    return {
        "messages": [ai_response], # 再次覆盖整个messages列表
        "search_results": [f"最终回复已生成"], # 覆盖整个search_results列表
        "sum_scores": 2.5
    }

# 5. 构建图
def build_graph():
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("input", input_node)
    workflow.add_node("search", search_node)
    workflow.add_node("response", response_node)

    # 设置边
    workflow.add_edge("input", "search")
    workflow.add_edge("search", "response")

    # 设置入口和出口
    workflow.set_entry_point("input")
    workflow.set_finish_point("response")

    return workflow.compile()

# 运行示例
if __name__ == "__main__":
    # 创建图实例
    app = build_graph()

    # 初始状态
    initial_state = {
        "query": "Python编程最佳实践",
        "messages": [SystemMessage(content="你是一个AI助手，正在进行信息检索任务。")],
        "search_results": []
    }

    # 执行
    result = app.invoke(initial_state)

    print("=== 最终状态 ===")
    print(f"查询: {result['query']}")

    print("\n=== 消息历史 ===")
    for i, msg in enumerate(result['messages']):
        print(f"[{i}] {msg.type}: {msg.content}")

    print("\n=== 搜索结果 ===")
    for i, res in enumerate(result['search_results']):
        print(f"[{i}] {res}")

    print("\n=== 数据求和结果 ===")
    print(result['sum_scores'])