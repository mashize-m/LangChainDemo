"""

    目标：通过问题搜索答案
        1. 定义图状态
        2. 定义节点函数
        3. 通过状态创建图实例
        4. 添加节点
        5. 添加边
        6. 编译图
        7. 启动工作流
        8. 输出结果

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

# 2. 定义节点函数
# def rag_node(state: MyState) -> MyState | dict:
#     query =  state['query']
#     rag_result = f"RAG检索结果：{query} , 从Milvus中检索一些数据..."
#     state['rag_result'] = rag_result
#     return state  #返回全量数据。即完整对象。   多节点并行执行，不允许返回整个state.

# 常用：只返回当前节点处理结果。属于MyState对象属性子集
def rag_node(state: MyState) -> MyState | dict:
    """RAG检索节点"""
    query = state['query']
    rag_result = f"RAG检索结果：{query} , 从Milvus中检索一些数据..."
    return {"rag_result": rag_result}  # 返回增量数据。注意："rag_result" 这个要跟 MyState 定义的名称保持一致。


def web_search_node(state: MyState) -> MyState | dict:
    """Web搜索节点"""
    query = state['query']
    web_search_result = f"Web检索结果：{query} , 从网上检索一些数据..."
    return {"web_search_result": web_search_result}  # 返回增量数据。即只返回当前节点处理结果。属于MyState对象属性子集


def final_answer_node(state: MyState) -> MyState | dict:
    """最终答案节点"""
    rag_result = state['rag_result']
    web_search_result = state['web_search_result']
    final_result = f"最终结果：{rag_result} , {web_search_result}"
    return {"final_result": final_result}


# 3. 通过状态创建图实例
graph = StateGraph(MyState)

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
state:MyState = {"query": "万用表如何使用?"}
final_state:MyState = compiled_graph.invoke(state)

# 8. 输出结果
final_result = final_state['final_result']
print(final_result)

# 打印图结构
#ImportError: Install grandalf to draw graphs: `pip install grandalf`.  科技手段
compiled_graph.get_graph().print_ascii()


"""
最终结果：RAG检索结果：万用表如何使用? , 从Milvus中检索一些数据... , Web检索结果：万用表如何使用? , 从网上检索一些数据...
             +-----------+                  
             | __start__ |                  
             +-----------+                  
            **           **                 
          **               **               
        **                   **             
+----------+           +-----------------+  
| rag_node |           | web_search_node |  
+----------+           +-----------------+  
            **           **                 
              **       **                   
                **   **                     
         +-------------------+              
         | final_answer_node |              
         +-------------------+              
                   *                        
                   *                        
                   *                        
              +---------+                   
              | __end__ |                   
              +---------+   
"""