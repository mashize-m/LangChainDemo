"""

    图的执行

        流式输出： 每个节点执行完，就可以打印节点结果。

        非流式输出，所有节点执行完，才能查看节点结果。



            获取节点nodes： 都是封装成PregelNode类型。

            获取channels：

                获取所有channels为： {
                    'aggregate': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x000002444DC45F40>,
                    '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC46F40>,
                    '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x000002444DC47180>,
                    'branch:to:a': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC472C0>,
                    'branch:to:b': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC54600>,
                    'branch:to:c': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC549C0>,
                    'branch:to:b_2': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC55340>,
                    'branch:to:d': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC55E40>
                }

            获取triggers：

                {
                    'a': ['branch:to:a'],
                    'b': ['branch:to:b'],
                    'c': ['branch:to:c'],
                    'b_2': ['branch:to:b_2'],
                    'd': ['branch:to:d']
                }

            获取writers： ChannelWrite

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
    graph.add_edge("b_2", "d")
    graph.add_edge("a", "c")
    graph.add_edge("c", "d")
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

    print("获取所有节点:", compiled_graph.nodes)

    print("获取所有channels为：", compiled_graph.channels)

    # 9. 查看 a 节点的 trigger（当前节点的订阅）和 writers
    print('节点a的triggers为', compiled_graph.nodes['a'].triggers, end="\n\n")
    print('节点a的writers为', compiled_graph.nodes['a'].writers, end="\n\n")

    # 10. 查看 d 节点的 trigger 和 writers
    print('当前图的节点d的triggers为', compiled_graph.nodes['d'].triggers, end="\n\n")
    print('当前图的节点d的writers为', compiled_graph.nodes['d'].writers, end="\n\n")

    # 9.打印流程图
    # compiled_graph.get_graph().print_ascii()


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


获取所有节点: {
    '__start__': <langgraph.pregel._read.PregelNode object at 0x00000165F210B700>, 
    'a': <langgraph.pregel._read.PregelNode object at 0x00000165F21090C0>, 
    'b': <langgraph.pregel._read.PregelNode object at 0x00000165F2108B20>, 
    'c': <langgraph.pregel._read.PregelNode object at 0x00000165F2109120>, 
    'b_2': <langgraph.pregel._read.PregelNode object at 0x00000165F2109F60>, 
    'd': <langgraph.pregel._read.PregelNode object at 0x00000165F2109210>
}

# 流程图底层通过 主题模式(发布与订阅模式)进行通信
获取所有channels为： {
    'aggregate': <langgraph.channels.binop.BinaryOperatorAggregate object at 0x000002444DC45F40>, 
    '__start__': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC46F40>, 
    '__pregel_tasks': <langgraph.channels.topic.Topic object at 0x000002444DC47180>, 
    'branch:to:a': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC472C0>, 
    'branch:to:b': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC54600>, 
    'branch:to:c': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC549C0>, 
    'branch:to:b_2': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC55340>, 
    'branch:to:d': <langgraph.channels.ephemeral_value.EphemeralValue object at 0x000002444DC55E40>
}





节点a的triggers为 ['branch:to:a']

节点a的writers为 [
ChannelWrite<...,...>(tags=None, recurse=True, explode_args=False, 
func_accepts={'config': ('N/A', <class 'inspect._empty'>)}, 
writes=(ChannelWriteTupleEntry(mapper=<function CompiledStateGraph.attach_node.<locals>._get_updates at 0x000001DDE1A8F910>, 
value=<object object at 0x000001DDE13A8A90>, static=None), 
ChannelWriteTupleEntry(mapper=<function _control_branch at 0x000001DDE1A8ECB0>,  value=<object object at 0x000001DDE13A8A90>, static=[]))), 

ChannelWrite<branch:to:b>(tags=None, recurse=True, explode_args=False, 
func_accepts={'config': ('N/A', <class 'inspect._empty'>)}, writes=(ChannelWriteEntry(channel='branch:to:b', value=None, skip_none=False, mapper=None),)), 

ChannelWrite<branch:to:c>(tags=None, recurse=True, explode_args=False, 
func_accepts={'config': ('N/A', <class 'inspect._empty'>)}, writes=(ChannelWriteEntry(channel='branch:to:c', value=None, skip_none=False, mapper=None),))]

当前图的节点d的triggers为 ['branch:to:d']

当前图的节点d的writers为 [
ChannelWrite<...,...>(tags=None, recurse=True, explode_args=False, func_accepts={'config': ('N/A', <class 'inspect._empty'>)}, 
writes=(ChannelWriteTupleEntry(mapper=<function CompiledStateGraph.attach_node.<locals>._get_updates at 0x000001DDE1A8FAC0>, 
value=<object object at 0x000001DDE13A8A90>, static=None), ChannelWriteTupleEntry(mapper=<function _control_branch at 0x000001DDE1A8ECB0>, 
value=<object object at 0x000001DDE13A8A90>, static=[])))]








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


"""
