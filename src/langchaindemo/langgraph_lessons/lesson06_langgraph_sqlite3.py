"""
LangGraph 状态存储示例：从checkpointer中恢复状态

uv add langgraph-checkpoint-sqlite
"""
import os
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import END
from langgraph.graph import START
from langgraph.graph import StateGraph


# 1. 构建图状态
class MyState(TypedDict):
    key_1: str
    key_2: str
    key_3: str


# 2. 定义节点函数
def node_1(state: MyState) -> MyState:
    print('node_1状态为', state)
    return {"key_1": "value_1"}


def node_2(state: MyState) -> MyState:
    print('node_2状态为', state)
    # raise Exception("模拟node_2节点报错")
    return {"key_2": "value_2"}


def node_3(state: MyState) -> MyState:
    print('node_3状态为', state)
    return {"key_3": "value_3"}


# 3. 构建图
def build_graph():
    graph = StateGraph(MyState)
    graph.add_node(node_1)
    graph.add_node(node_2)
    graph.add_node(node_3)

    graph.add_edge(START, "node_1")

    graph.add_edge("node_1", "node_2")
    graph.add_edge("node_1", "node_3")

    graph.add_edge("node_2", END)
    graph.add_edge("node_3", END)
    return graph


# 4. 主函数
def demo_langgraph():
    #创建sqlite数据的存储目录。不存在就新建，存在什么都不做。
    os.makedirs("./sqlite_data", exist_ok=True)
    #创建数据存储文件。check_same_thread默认true,表示只能同一线程使用这个数据库。
    #解决断点续传问题。check_same_thread必须设置为False.表示允许多个线程操作数据库。
    conn = sqlite3.connect(database="./sqlite_data/langgraph_sqlite.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn) #长期记忆数据库。可以更换成mgdb等其他数据库

    # 3. 构建图
    graph = build_graph()

    # 4. 编译图时传入 Checkpointer
    compiled_graph = graph.compile(checkpointer=checkpointer)

    # 5. 定义config
    config = {"configurable": {"thread_id": "a1"}}

    # 6. 调用时传入config
    # result = compiled_graph.invoke({}, config=config)  #

    # # 6. 从状态中恢复：传入None。不能传 {} 空对象，这个会跑新的流程
    result = compiled_graph.invoke(None, config=config)

    # 7. 打印结果
    print(result)
    # compiled_graph.get_graph().print_ascii()


if __name__ == "__main__":
    demo_langgraph()