"""

    节点重试

"""

from typing import Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from typing_extensions import TypedDict

# 1. 定义状态
class State(TypedDict):
    result: str

# 2. 模拟不稳定的API调用，使用全局变量跟踪尝试次数
def unstable_node(state: State) -> Dict[str, Any]:
    """
    模拟一个不稳定的API调用，有一定概率失败
    """
    global attempt_counter
    attempt_counter += 1
    print(f"尝试调用API，这是第 {attempt_counter} 次尝试")
    # 模拟前几次尝试失败，最后一次成功
    if attempt_counter < 3:
        #raise Exception(f"模拟API调用失败 (尝试 {attempt_counter})")
        #raise ConnectionError(f"模拟网络连接失败 (尝试 {attempt_counter})")
        raise ValueError(f"模拟数据错误 (尝试 {attempt_counter})")
    else:
        # 第三次尝试成功
        return {
            "result": f"API调用成功，经过 {attempt_counter} 次尝试"
        }

# 3. 构建图
def build_graph():
    graph = StateGraph(State)
    # 添加节点，使用默认重试策略，允许最多5次尝试
    # 注意：默认策略会自动排除编程错误等不可恢复的异常
    graph.add_node(
        "unstable_node",
        unstable_node,
        #retry_policy=RetryPolicy(max_attempts=5)
        retry_policy=RetryPolicy(max_attempts=5,retry_on=[ConnectionError,TimeoutError])
    )
    # 添加边
    graph.add_edge(START, "unstable_node")
    graph.add_edge("unstable_node", END)
    return graph.compile()

# 4. 主函数
def demo_langgraph():
    # 重置全局计数器
    global attempt_counter
    attempt_counter = 0

    app = build_graph()
    try:
        result = app.invoke({"result": ""})
        print(f"最终结果: {result}\n")
    except Exception as e:
        print(f"最终失败: {type(e).__name__}: {e}\n")

# 运行
if __name__ == "__main__":
    demo_langgraph()