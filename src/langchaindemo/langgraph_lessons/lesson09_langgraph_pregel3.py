"""

    图的执行

            通过历史查看节点状态：

                get_state(config=config)

                get_state_history(config=config)
"""
import operator
import os
import sqlite3
from typing import TypedDict, Annotated, List

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph


# 1.定义图状态
class State(TypedDict):
    aggregate: Annotated[List[str], operator.add]  # 聚合每个节点返回的结合   累加


# 2.定义节点
def a(state: State) -> dict[str, str]:
    print(f"Adding 'A' to {state['aggregate']}")
    return {"aggregate": ['A']}


def b(state: State) -> dict[str, str]:
    print(f"Adding 'B' to {state['aggregate']}")
    return {"aggregate": ['B']}


def c(state: State) -> dict[str, str]:
    print(f"Adding 'C' to {state['aggregate']}")
    return {"aggregate": ['C']}


def b_2(state: State) -> dict[str, str]:
    print(f"Adding 'B_2' to {state['aggregate']}")
    return {"aggregate": ['B_2']}


def d(state: State) -> dict[str, str]:
    print(f"Adding 'D' to {state['aggregate']}")
    return {"aggregate": ['D']}


def build_graph():
    # 3.创建图对象
    graph = StateGraph(State)

    # 4.添加节点
    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(c)
    graph.add_node(b_2)
    graph.add_node(d)

    # 5.添加边
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "b_2")
    graph.add_edge("b_2", "d")
    graph.add_edge("a", "c")
    graph.add_edge("c", "d")
    graph.add_edge("d", END)

    return graph


def main():
    # 6.编译图
    graph = build_graph()

    #checkpointer = InMemorySaver()
    # 初始化数据库连接和 Checkpointer
    os.makedirs("./sqlite_data", exist_ok=True)
    conn = sqlite3.connect(database="./sqlite_data/checkpointer.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    app = graph.compile(checkpointer=checkpointer)

    compiled_graph = graph.compile(checkpointer=checkpointer)

    # 7.执行图
    state = {
        "aggregate": []
    }
    config = {
        "configurable": {
            "thread_id": "333"
        }
    }
    final_state = compiled_graph.invoke(input=state, config=config)
    print(final_state)

    # 8.获取最近的状态
    print("获取最近的状态", compiled_graph.get_state(config=config))

    all_states = compiled_graph.get_state_history(config=config)
    all_states_list = list(all_states)
    print("获取所有节点状态:")
    for state in all_states_list:
        print(state)

    """
    获取最近的状态 StateSnapshot(values={'aggregate': ['A', 'B', 'C', 'B_2', 'D', 'D']}, next=(), 
    config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e7c-d461-6859-8004-261371526e6c'}}, 
    metadata={'source': 'loop', 'step': 4, 'parents': {}}, created_at='2026-08-17T03:00:28.561416+00:00', 
    parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e7c-d45f-617a-8003-670115b76fab'}}, tasks=(), interrupts=())
    
    
    获取所有节点状态:
        StateSnapshot(values={'aggregate': ['A', 'B', 'C', 'B_2', 'D', 'D']}, next=(), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e37-6b45-8004-cb6c5d1da1ba'}}, metadata={'source': 'loop', 'step': 4, 'parents': {}}, created_at='2026-08-17T03:04:21.118445+00:00', parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e35-6562-8003-be42eed162be'}}, tasks=(), interrupts=())
        StateSnapshot(values={'aggregate': ['A', 'B', 'C', 'B_2', 'D']}, next=('d',), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e35-6562-8003-be42eed162be'}}, metadata={'source': 'loop', 'step': 3, 'parents': {}}, created_at='2026-08-17T03:04:21.117475+00:00', parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e30-6660-8002-97a1ace9b722'}}, tasks=(PregelTask(id='34ef7ae2-3f38-fd2b-418b-11ffc18ac069', name='d', path=('__pregel_pull', 'd'), error=None, interrupts=(), state=None, result={'aggregate': ['D']}),), interrupts=())
        StateSnapshot(values={'aggregate': ['A', 'B', 'C']}, next=('b_2', 'd'), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e30-6660-8002-97a1ace9b722'}}, metadata={'source': 'loop', 'step': 2, 'parents': {}}, created_at='2026-08-17T03:04:21.114481+00:00', parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e26-6b45-8001-d82f03c888a6'}}, tasks=(PregelTask(id='d9347f4b-17f2-3c75-0844-9938a150062a', name='b_2', path=('__pregel_pull', 'b_2'), error=None, interrupts=(), state=None, result={'aggregate': ['B_2']}), PregelTask(id='30a8e10e-2874-b0ba-3599-bc42c7d1d6c0', name='d', path=('__pregel_pull', 'd'), error=None, interrupts=(), state=None, result={'aggregate': ['D']})), interrupts=())
        StateSnapshot(values={'aggregate': ['A']}, next=('b', 'c'), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e26-6b45-8001-d82f03c888a6'}}, metadata={'source': 'loop', 'step': 1, 'parents': {}}, created_at='2026-08-17T03:04:21.111482+00:00', parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e21-6ce4-8000-96a570afdc4f'}}, tasks=(PregelTask(id='c5cb5cb4-b4ff-ba78-96b1-b367cf96541a', name='b', path=('__pregel_pull', 'b'), error=None, interrupts=(), state=None, result={'aggregate': ['B']}), PregelTask(id='d764e847-80f1-44b0-808f-4bf7766fe90a', name='c', path=('__pregel_pull', 'c'), error=None, interrupts=(), state=None, result={'aggregate': ['C']})), interrupts=())
        StateSnapshot(values={'aggregate': []}, next=('a',), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e21-6ce4-8000-96a570afdc4f'}}, metadata={'source': 'loop', 'step': 0, 'parents': {}}, created_at='2026-08-17T03:04:21.109475+00:00', parent_config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e1f-61e4-bfff-f0369a6a1cd7'}}, tasks=(PregelTask(id='c1cd59b5-24bd-03f4-f9c9-f177fe80f7d1', name='a', path=('__pregel_pull', 'a'), error=None, interrupts=(), state=None, result={'aggregate': ['A']}),), interrupts=())
        StateSnapshot(values={'aggregate': []}, next=('__start__',), config={'configurable': {'thread_id': '333', 'checkpoint_ns': '', 'checkpoint_id': '1f199e85-7e1f-61e4-bfff-f0369a6a1cd7'}}, metadata={'source': 'input', 'step': -1, 'parents': {}}, created_at='2026-08-17T03:04:21.108374+00:00', parent_config=None, tasks=(PregelTask(id='49181e75-1611-8738-010b-d06e4663425e', name='__start__', path=('__pregel_pull', '__start__'), error=None, interrupts=(), state=None, result={'aggregate': []}),), interrupts=())


    """
if __name__ == "__main__":
    main()
