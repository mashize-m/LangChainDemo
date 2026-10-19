"""
新增了几个类型，然后在输入前、输出前、node节点时候用。
相当于把 MyState 复制了一份，在某些特定节点函数的时候，定义单独的类型。

"""
from typing import TypedDict

from langgraph.constants import START, END
from langgraph.graph import StateGraph

# 1. 定义图状态：  状态对象给各个节点使用的。
class MyState(TypedDict):
    query: str = None  # 输入问题
    rag_result: str  = None# RAG检索结果 -  从Milvus数据库中检查文档
    web_search_result: str = None # Web搜索结果
    final_result: str = None # 将两路检索结果进行合并  ： rag_result + web_search_result


class InputState(TypedDict):
    query: str = None

class OutputState(TypedDict):
    final_result: str = None

# 2. 定义节点函数
def rag_node(state: InputState) -> MyState | dict:
    """RAG检索节点"""
    query = state['query']
    rag_result = f"RAG检索结果：{query} , 从Milvus中检索一些数据..."
    return {"rag_result": rag_result}  # 返回增量数据。即只返回当前节点处理结果。属于MyState对象属性子集


def web_search_node(state: InputState) -> MyState | dict:
    """Web搜索节点"""
    query = state['query']
    web_search_result = f"Web检索结果：{query} , 从网上检索一些数据..."
    return {"web_search_result": web_search_result}  # 返回增量数据。即只返回当前节点处理结果。属于MyState对象属性子集


def final_answer_node(state: MyState) -> OutputState:
    """最终答案节点"""
    rag_result = state['rag_result']
    web_search_result = state['web_search_result']
    final_result = f"最终结果：{rag_result} , {web_search_result}"
    return {"final_result222": final_result,"query": "query111"}


# 3. 通过状态创建图实例
graph = StateGraph(
    state_schema=MyState,
    input_schema=InputState,
    output_schema=OutputState
)

# 4. 添加节点
graph.add_node(rag_node)
graph.add_node(web_search_node)
graph.add_node(final_answer_node)

# 5. 添加边
graph.add_edge(START, "rag_node")
graph.add_edge(START, "web_search_node")
graph.add_edge("rag_node", "final_answer_node")
graph.add_edge("web_search_node", "final_answer_node")
graph.add_edge("final_answer_node", END)

# 6. 编译图
compiled_graph = graph.compile()

# 7. 启动工作流
state:InputState = {"query": "万用表如何使用?"}
final_state:OutputState = compiled_graph.invoke(state)
print(final_state)


# 打印图结构
#ImportError: Install grandalf to draw graphs: `pip install grandalf`.  科技手段
compiled_graph.get_graph().print_ascii()
