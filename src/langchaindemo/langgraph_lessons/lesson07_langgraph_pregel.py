"""

    图的执行

        流式输出： 每个节点执行完，就可以打印节点结果。

        非流式输出，所有节点执行完，才能查看节点结果。

            D节点执行一次还是两次?

"""
import operator
from typing import TypedDict, Annotated, List

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
    #graph.add_edge("b_2", "d") # b_2执行完，d执行一次
    graph.add_edge("a", "c")
    #graph.add_edge("c", "d")  # c执行完，d执行一次

    graph.add_edge(["b_2","c"], "d") # 等b_2和c都执行完,d才会执行。d只执行一次。
    graph.add_edge("d", END)

    return graph


def main():
    # 6.编译图
    graph = build_graph()
    compiled_graph = graph.compile()

    # 7.执行图
    state = {
        "aggregate": []
    }
    final_state = compiled_graph.invoke(state)  # 非流式输出
    # compiled_graph.stream() #流式输出

    # 8.解析结果
    print("最终状态", final_state)

    # 9.打印流程图
    compiled_graph.get_graph().print_ascii()


if __name__ == "__main__":
    main()


"""
Adding 'A' to []
Adding 'B' to ['A']
Adding 'C' to ['A']
Adding 'B_2' to ['A', 'B', 'C']
Adding 'D' to ['A', 'B', 'C']
Adding 'D' to ['A', 'B', 'C', 'B_2', 'D']
最终状态 {'aggregate': ['A', 'B', 'C', 'B_2', 'D', 'D']}
  +-----------+   
  | __start__ |   
  +-----------+   
         *        
         *        
         *        
      +---+       
      | a |       
      +---+*      
      *     *     
     *      *     
    *        *    
 +---+        *   
 | b |        *   
 +---+        *   
    *         *   
    *         *   
    *         *   
+-----+     +---+ 
| b_2 |     | c | 
+-----+     +---+ 
      *     *     
       *   *      
        * *       
      +---+       
      | d |       
      +---+       
         *        
         *        
         *        
    +---------+   
    | __end__ |   
    +---------+   


# d节点增加屏障，必须等到b_2和c全部执行完，才执行d节点。
Adding 'A' to []
Adding 'B' to ['A']
Adding 'C' to ['A']
Adding 'B_2' to ['A', 'B', 'C']
Adding 'D' to ['A', 'B', 'C', 'B_2']
最终状态 {'aggregate': ['A', 'B', 'C', 'B_2', 'D']}
"""