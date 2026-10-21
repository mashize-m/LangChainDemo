
"""

    递归节点调用，可控循环。必须程序无法终止,系统崩溃。


"""


from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError

# 1. 定义状态
class LoopState(TypedDict):
    count: int        # 当前计数
    result: str       # 结果信息
    max_count: int    # 业务逻辑上的终止阈值

# 2. 定义节点
def node_a(state: LoopState) -> dict:
    """节点A：主处理逻辑，增加计数"""
    print(f"执行节点A，当前计数: {state['count']}")
    return {
        'count': state['count'] + 1,
        'result': f"已处理 {state['count']} 次"
    }

def node_b(state: LoopState) -> dict:
    """节点B：辅助处理"""
    print(f"执行节点B，当前计数: {state['count']}")
    return {
        'result': f"已处理 {state['count']} 次 - 辅助处理"
    }

# 3. 定义条件路由
def route(state: LoopState) -> Literal["b", END]:
    """
    条件路由：
    如果 count >= max_count，则结束；否则去往节点B，形成循环。
    """
    if state['count'] >= state['max_count']:
        print(f"结束循环。")
        return END
    else:
        print(f"继续循环...")
        return "b"

# 4. 构建图
def build_graph():
    graph = StateGraph(LoopState)
    graph.add_node("a", node_a)
    graph.add_node("b", node_b)

    # 构建循环结构: START -> A -> (B -> A) ... -> END
    graph.add_edge(START, "a")
    graph.add_conditional_edges("a", route)
    graph.add_edge("b", "a")

    return graph.compile()

if __name__ == "__main__":
    app = build_graph()

    try:
        # 注意：这里设置业务逻辑需要循环10次才能自然结束
        # 但我们在 config 中将 recursion_limit 设置为 6
        result = app.invoke(
            input={
                'count': 0,
                'max_count': 10
            },
            config={
                'recursion_limit': 6  # 强制限制：最多只允许运行6次
            }
        )
        print("=== 执行成功 ===")
        print(result)

    except GraphRecursionError as e:
        print(f"\n[系统警告] 捕获到递归错误: {e}")
        print("原因：图执行步数超过了 config 中设定的 recursion_limit。")