"""

    节点缓存

"""

import time

from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import CachePolicy
from typing_extensions import TypedDict

# 1. 定义图状态
class State(TypedDict):
    x: int
    result: int

# 2. 节点函数：模拟一些有耗时计算的节点
def expensive_node(state: State) -> dict[str, int]:
    # expensive computation
    print(f"expensive_node 被调用")
    time.sleep(5) # 模拟耗时计算
    print(f"expensive_node 计算完成")
    return {"result": state["x"] * 2}

# 3. 构建图
def build_graph():
    graph = StateGraph(State)

    # 添加节点时，为节点配置缓存策略，这里设置为10秒缓存
    graph.add_node("expensive_node", expensive_node, cache_policy=CachePolicy(ttl=10))  # time to live  存活时间

    graph.add_edge(START, "expensive_node")
    graph.add_edge("expensive_node", END)
    return graph

# 4. 主函数
def demo_langgraph():

    # 1. 构建图
    graph = build_graph()

    # 3. 图编译时，传入缓存器，此处使用InMemoryCache，也可以使用RedisCache等
    app = graph.compile(cache=InMemoryCache())

    # 3、第一次调用，传入的状态为5
    print(app.invoke({"x": 5}))

    time.sleep(3)

    # 4、第二次调用，传入相同的状态，由于缓存策略，会直接从缓存中返回结果，而不会重新调用节点
    print(app.invoke({"x": 5}))

if __name__ == "__main__":
    demo_langgraph()