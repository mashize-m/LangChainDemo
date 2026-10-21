# 04_nodes/01_node_parameters_demo.py

"""
客服系统案例

    三大输入参数：state, config, runtime

"""

from typing import TypedDict, List

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime


# 1. 模拟大模型客户端
class MockLLM:
    def invoke(self, prompt: str):
        return f"AI生成答案：'{prompt}'"


# 2. 模拟数据库客户端
class MockDatabase:
    def get_user_info(self, user_id: str):
        return {"id": user_id, "role": "vip" if "vip" in user_id else "standard"}

# 3. 定义图状态
class CustomerSupportState(TypedDict):
    query: str  # 用户问题
    response: str  # 客服回复
    log: List[str]  # 处理日志


# 4. 创建节点函数
def node_customer_service(state: CustomerSupportState, config: RunnableConfig, runtime: Runtime) -> dict:

    # 1 【参数1演示】从 state 中读取用户输入
    user_query = state["query"]
    print(f"[State] 用户问题: {user_query}")

    # 2 【参数2演示】从 config 中获取注入的依赖和用户配置
    configurable = config.get("configurable")
    user_id = configurable.get("user_id", "guest") # 如果没有则设置为 guest
    print(f"[config] 开始处理，User ID: {user_id}")

    # 3 【参数3演示】从runtime当中获取context对象
    llm_client = runtime.context['llm_client']
    db_client = runtime.context['db_client']
    # 验证是否存在  降级处理
    if not llm_client or not db_client:
        return {
            "response": "系统错误: 依赖未注入",
            "log": ["错误: LLM 或 DB 未在 config 中配置"]
        }

    # 使用db对象查看用户角色
    user_info = db_client.get_user_info(user_id)
    user_role = user_info.get("role")
    print(f"[runtime] 从 DB 获取用户角色: {user_role}")

    # 根据用户角色构建不同的 Prompt，并模拟 LLM 调用
    prompt = f"用户({user_role})提问: {user_query}"
    llm_response = llm_client.invoke(prompt)

    return {
        "response": llm_response,
        "log": ["成功：任务结束"]
    }


# 5. 构建图
def build_graph():
    workflow = StateGraph(CustomerSupportState)
    workflow.add_node(node_customer_service)
    workflow.add_edge(START, "node_customer_service")
    workflow.add_edge("node_customer_service", END)
    return workflow.compile()


# 运行示例
if __name__ == "__main__":

    # 创建图实例
    app = build_graph()

    # 初始化状态对象
    initial_state = {"query": "如何升级会员？"}

    # 初始化config对象
    config = {
        "configurable": {
            "user_id": "vip_user_999",
        }
    }

    # 初始化上下文运行环境
    context = {
        "llm_client": MockLLM(),
        "db_client": MockDatabase()
    }

    # 运行
    print("[System] 开始运行图，并注入依赖对象...")
    result = app.invoke(input=initial_state, config=config, context=context)
    print(result)