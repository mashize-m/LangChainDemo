"""

    演示错误开发案例：

        并行节点不能返回全量state对象。
        多个并行节点都返回同一个属性，会出现冲突：
          langgraph.errors.InvalidUpdateError: At key 'query': Can receive only one value per step. Use an Annotated key to handle multiple values.


        解决： 使用reducer函数。或返回增量状态数据。

"""

# 04_nodes/02_node_output_wrong_demo.py

from typing import TypedDict

from langgraph.constants import START,END
from langgraph.graph import StateGraph

class MyState(TypedDict):
        query:str
        file_result:str
        web_result:str
        final_answer:str

def query_web(state:MyState)->dict:
    """
    网络搜索，返回搜索结果
    """
    # 1、错误演示：直接return整个state，而非当前节点增量修改的状态
    query = state['query']
    state['web_result'] = f'{query}的网络搜索结果'
    return state

def query_file(state:MyState)->dict:
    """
    文件搜索，返回搜索结果
    """
    query = state['query']
    state['file_result'] = f'{query}的文件搜索结果'
    return state

def answer(state:MyState)->dict:
    """
    返回最终的答案
    """
    web_result = state['web_result']
    file_result = state['file_result']
    final_answer = f'LLM基于{web_result}，{file_result} 的最终结果'
    state['final_answer'] = final_answer
    return state

# 5. 构建图
def build_graph():
    graph = StateGraph(MyState)
    graph.add_node(answer)
    graph.add_node(query_web)
    graph.add_node(query_file)
    graph.add_edge(START,'query_web')
    graph.add_edge(START,'query_file')
    graph.add_edge('query_web','answer')
    graph.add_edge('query_file','answer')
    graph.add_edge('answer',END)
    return graph.compile()

if __name__ == '__main__':
    app = build_graph()
    init_state = {"query":"什么是Langgraph"}
    final_state = app.invoke(init_state)
    print(final_state['final_answer'])