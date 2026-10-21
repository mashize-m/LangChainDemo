
"""

     条件边

"""

from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


# 1. 定义状态
class GraphState(TypedDict):
    value: int
    step: str


# 2. 定义节点函数
def node_a(state: GraphState) -> dict:
    """节点A：作为决策前的处理节点"""
    print("执行节点A")
    return {"value": state["value"], "step": "A执行完毕"}


def node_b(state: GraphState) -> dict:
    """节点B：处理偶数逻辑"""
    print("执行节点B")
    return {"value": state["value"] * 2, "step": "B执行完毕"}


def node_c(state: GraphState) -> dict:
    """节点C：处理奇数逻辑"""
    print("执行节点C")
    return {"value": state["value"] - 1, "step": "C执行完毕"}


# 3. 定义路由函数
def route_condition(state: GraphState) -> Literal["node_b_alias", "node_c_alias"]:
    """
    根据 value 值决定路由到哪个节点
    注意：这里返回的是别名（Alias），用于在映射表中查找
    """
    if state["value"] % 2 == 0:
        return "node_b_alias"  # 偶数路由到节点B
    else:
        return "node_c_alias"  # 奇数路由到节点C


# 4. 构建图
def build_graph():
    # 创建图构建器
    graph = StateGraph(GraphState)

    # 添加节点
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_node("node_c", node_c)

    # 添加入口边
    # 通过条件边来控制节点的执行：   如果输入参数value是偶数，走B节点；是奇数，走C节点
    graph.add_edge(START, "node_a")
    graph.add_conditional_edges(
        "node_a",
        route_condition,
        {"node_b_alias": "node_b", "node_c_alias": "node_c"},
    )
    graph.add_edge("node_b", END)
    graph.add_edge("node_c", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    # 情况1：输入值为偶数
    print("\n输入值为偶数 (2):")
    result = app.invoke({"value": 2})
    print(f"执行结果: {result}")

    # 情况2：输入值为奇数
    print("\n输入值为奇数 (1):")
    result = app.invoke({"value": 1})
    print(f"执行结果: {result}")
