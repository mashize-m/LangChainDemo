
"""

    流式输出模式演示

    values、updates、custom、messages、debug、混合模式

"""

import os
import time
from typing import TypedDict, Annotated, List
import operator

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime


# 初始化 LLM
llm_client = init_chat_model(
    model="qwen3.6-flash",
    model_provider="openai",
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)


# 1. 定义图状态
class State(TypedDict):
    input: str
    messages: Annotated[List[BaseMessage], operator.add]
    current_step: str


# 2. 定义节点
def node_input(state: State):
    """接收用户输入"""
    input = state["input"]
    return {
        "messages": [HumanMessage(content=input)],
        "current_step": "step1-接收用户输入"
    }

# 3. 定义节点
def node_processing(state: State, runtime: Runtime):
    """
    模拟中间处理过程，并使用 writer 输出自定义流式数据
    这对应 stream_mode="custom"
    """
    steps = ["正在分析意图...", "正在检索知识库...", "正在构建Prompt..."]
    writer = runtime.stream_writer

    for i, step in enumerate(steps):
        time.sleep(0.5)  # 模拟耗时操作

        # 使用 writer 发送自定义数据 (不影响图的状态)
        # 这些数据只能通过 stream_mode="custom" 接收到
        writer({
            "step_index": i + 1,
            "description": step,
            "timestamp": time.time()
        })

    return {"current_step": "step2-处理完成"}

# 4. 定义节点
def node_generation(state: State):
    """
    LLM 生成答案
    LangGraph 的 stream_mode="messages" 会自动捕获 LLM 的流式输出
    """
    # 调用 LLM
    response = llm_client.invoke(state["messages"])

    return {
        "messages": [response],
        "current_step": "step3-LLM答案生成完成"
    }


# 5. 构建图
def build_graph():

    graph = StateGraph(State)
    graph.add_node("input", node_input)
    graph.add_node("process", node_processing)
    graph.add_node("generate", node_generation)

    graph.add_edge(START, "input")
    graph.add_edge("input", "process")
    graph.add_edge("process", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# 4. 演示不同的流式输出模式
def demo_langgraph():

    initial_state = {"input": "我是谁", "messages": [], "current_step": "start"}
    app = build_graph()


    # 0. Mode: None
    print(f"\n{'=' * 20} 0. Mode: 不指定 {'=' * 20}")
    print("描述: 每执行完一个节点，输出当前的完整 State")
    for event in app.stream(input=initial_state):
        print(f"State: {event}")
    """
    ==================== 0. Mode: 不指定 ====================
    描述: 每执行完一个节点，输出当前的完整 State
    State: {'input': {'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={})], 'current_step': 'step1-接收用户输入'}}
    State: {'process': {'current_step': 'step2-处理完成'}}
    State: {'generate': {'messages': [AIMessage(content='作为一个人工智能，我无法知道您的真实身份。我没有访问您个人信息的权限，也不会记忆或存储任何用户的私人数据。\n\n如果您是出于好奇或哲学思考提出这个问题，我们可以一起探讨“自我认知”“身份认同”等话题；如果您是在实际场景中需要梳理个人信息、填写资料，或想通过对话更清晰地认识自己，也可以告诉我具体情境，我会尽力为您提供参考建议。', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 625, 'prompt_tokens': 12, 'total_tokens': 637, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 538, 'rejected_prediction_tokens': None, 'text_tokens': 625}, 'prompt_tokens_details': {'audio_tokens': None, 'cache_write_tokens': None, 'cached_tokens': None, 'text_tokens': 12}}, 'model_provider': 'openai', 'model_name': 'qwen3.6-flash', 'system_fingerprint': None, 'id': 'chatcmpl-bb3b5bf7-c498-9907-bfb9-de00012765fd', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--01a00e8d-898e-7080-b205-f6030605d083-0', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 12, 'output_tokens': 625, 'total_tokens': 637, 'input_token_details': {}, 'output_token_details': {'reasoning': 538}})], 'current_step': 'step3-LLM答案生成完成'}}
    """


    # 1. Mode: values (输出完整状态)
    # print(f"\n{'=' * 20} 1. Mode: values {'=' * 20}")
    # print("描述: 每执行完一个节点，输出当前的完整 State")
    # for event in app.stream(input=initial_state, stream_mode="values"):
    #     # print(f"State: keys={list(event.keys())}, step={event.get('current_step')}")
    #     print(f"State: {event}")

    """
    ==================== 1. Mode: values ====================
    描述: 每执行完一个节点，输出当前的完整 State
    State: {'input': '我是谁', 'messages': [], 'current_step': 'start'}
    State: {'input': '我是谁', 'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={})], 'current_step': 'step1-接收用户输入'}
    State: {'input': '我是谁', 'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={})], 'current_step': 'step2-处理完成'}
    State: {'input': '我是谁', 'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={}), AIMessage(content='作为一个人工智能，我无法知道您的真实身份。每次对话对我来说都是独立的，我没有记忆功能，也无法访问或记录任何个人数据。如果您愿意告诉我您希望我怎么称呼您，或者分享一些背景信息，我很乐意在了解您的需求后为您提供更贴合的帮助！😊', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 423, 'prompt_tokens': 12, 'total_tokens': 435, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 362, 'rejected_prediction_tokens': None, 'text_tokens': 423}, 'prompt_tokens_details': {'audio_tokens': None, 'cache_write_tokens': None, 'cached_tokens': None, 'text_tokens': 12}}, 'model_provider': 'openai', 'model_name': 'qwen3.6-flash', 'system_fingerprint': None, 'id': 'chatcmpl-85c278ad-8eb1-9acd-a3cf-e1b8e63a5bcd', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--01a00e78-7586-7ff0-b606-e0c86b9a3860-0', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 12, 'output_tokens': 423, 'total_tokens': 435, 'input_token_details': {}, 'output_token_details': {'reasoning': 362}})], 'current_step': 'step3-LLM答案生成完成'}

    """

    #
    # 2. Mode: updates (输出增量更新)
    # print(f"\n{'=' * 20} 2. Mode: updates {'=' * 20}")
    # print("描述: 每执行完一个节点，输出该节点返回的增量数据")
    # for event in app.stream(initial_state, stream_mode="updates"):
    #     print(f"Update: {event}")

    """
    ==================== 2. Mode: updates ====================
    描述: 每执行完一个节点，输出该节点返回的增量数据
    Update: {'input': {'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={})], 'current_step': 'step1-接收用户输入'}}
    Update: {'process': {'current_step': 'step2-处理完成'}}
    Update: {'generate': {'messages': [AIMessage(content='我是一个 AI 助手，无法知道您的具体身份。如果您愿意分享更多信息，我很乐意提供帮助！', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 187, 'prompt_tokens': 12, 'total_tokens': 199, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 162, 'rejected_prediction_tokens': None, 'text_tokens': 187}, 'prompt_tokens_details': {'audio_tokens': None, 'cache_write_tokens': None, 'cached_tokens': None, 'text_tokens': 12}}, 'model_provider': 'openai', 'model_name': 'qwen3.6-flash', 'system_fingerprint': None, 'id': 'chatcmpl-b8169791-170e-99c3-9cdf-38e61beecb65', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--01a00e7c-381d-7571-be97-2a44e23f73d0-0', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 12, 'output_tokens': 187, 'total_tokens': 199, 'input_token_details': {}, 'output_token_details': {'reasoning': 162}})], 'current_step': 'step3-LLM答案生成完成'}}

    """

    # 3. Mode: custom (输出自定义数据)
    # print(f"\n{'=' * 20} 3. Mode: custom {'=' * 20}")
    # print("描述: 仅输出节点内部通过 writer() 发送的数据")
    # for event in app.stream(initial_state, stream_mode="custom"):
    #     print(f"Custom Data: {event}")


    """
    ==================== 3. Mode: custom  结合 runtime.stream_writer====================
    描述: 仅输出节点内部通过 writer() 发送的数据
    Custom Data: {'step_index': 1, 'description': '正在分析意图...', 'timestamp': 1786949639.8489828}
    Custom Data: {'step_index': 2, 'description': '正在检索知识库...', 'timestamp': 1786949640.3629596}
    Custom Data: {'step_index': 3, 'description': '正在构建Prompt...', 'timestamp': 1786949640.877918}
    """

    # # 4. Mode: messages (输出 LLM Token)
    # print(f"\n{'=' * 20} 4. Mode: messages {'=' * 20}")
    # print("描述: 输出 LLM 生成的消息片段 (Token)")
    # for chunk, metadata in app.stream(initial_state, stream_mode="messages"):
    #     node_name = metadata.get('langgraph_node', 'unknown')
    #     # 打印 Token 内容，模拟打字机效果
    #     print(f"[{node_name}] Token: {chunk.content!r}")
    #     time.sleep(0.1)  # 仅用于演示视觉效果
    #
    # 5. Mode: debug (调试模式)
    # print(f"\n{'=' * 20} 5. Mode: debug {'=' * 20}")
    # print("描述: 输出所有详细的执行信息")
    # count = 0
    # for event in app.stream(initial_state, stream_mode="debug"):
    #     if count < 30:  # 仅演示前几条
    #         print(event)
    #         #print(f"Debug Event: {event['type']} - {event.get('payload', {}).get('name')}")
    #     count += 1
    # print("... (省略后续 debug 信息)")
    #
    # 6. Mixed Mode (混合模式)
    # print(f"\n{'=' * 20} 6. Mixed Mode {'=' * 20}")
    # print("描述: 同时获取 updates 和 custom 数据")
    # for mode, data in app.stream(initial_state, stream_mode=["updates", "custom"]):
    #     if mode == "updates":
    #         print(f"[Updates] 来自节点 {data}")
    #     elif mode == "custom":
    #         print(f"[Custom] {data}")

    """
    ==================== 6. Mixed Mode ====================
    描述: 同时获取 updates 和 custom 数据
    [Updates] 来自节点 {'input': {'messages': [HumanMessage(content='我是谁', additional_kwargs={}, response_metadata={})], 'current_step': 'step1-接收用户输入'}}
    [Custom] {'step_index': 1, 'description': '正在分析意图...', 'timestamp': 1786950073.1511722}
    [Custom] {'step_index': 2, 'description': '正在检索知识库...', 'timestamp': 1786950073.6668932}
    [Custom] {'step_index': 3, 'description': '正在构建Prompt...', 'timestamp': 1786950074.1679606}
    [Updates] 来自节点 {'process': {'current_step': 'step2-处理完成'}}
    [Updates] 来自节点 {'generate': {'messages': [AIMessage(content='作为一个人工智能，我无法知道你具体的身份或姓名。出于隐私保护和技术设计，我不会记录或获取用户的个人信息，每次对话对我而言都是“全新”的。\n\n不过，你是谁并不重要，重要的是你想成为什么样的人、正在经历什么、需要解决什么问题。如果你愿意分享你的名字、兴趣、目标，或者只是随便聊聊，我很乐意在这里认真倾听、陪你探讨或提供力所能及的帮助。你今天想聊点什么呢？', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 509, 'prompt_tokens': 12, 'total_tokens': 521, 'completion_tokens_details': {'accepted_prediction_tokens': None, 'audio_tokens': None, 'reasoning_tokens': 416, 'rejected_prediction_tokens': None, 'text_tokens': 509}, 'prompt_tokens_details': {'audio_tokens': None, 'cache_write_tokens': None, 'cached_tokens': None, 'text_tokens': 12}}, 'model_provider': 'openai', 'model_name': 'qwen3.6-flash', 'system_fingerprint': None, 'id': 'chatcmpl-5b3521ea-ad89-9d5b-9745-0d35f340e618', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--01a00e86-3f3b-7ff3-8c64-d1d1d06c7a14-0', tool_calls=[], invalid_tool_calls=[], usage_metadata={'input_tokens': 12, 'output_tokens': 509, 'total_tokens': 521, 'input_token_details': {}, 'output_token_details': {'reasoning': 416}})], 'current_step': 'step3-LLM答案生成完成'}}
    """

if __name__ == "__main__":
    demo_langgraph()