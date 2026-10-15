import asyncio
import time

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI
from anthropic import BaseModel
from pydantic import Field

from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
import json


def main() -> None:
    """
    llm常用接口案例
    """

    """
    1、生成实例方式
    """
    client = init_chat_model(
    	model=OPENAI_MODEL,
    	model_provider="openai",
    )

    # client = ChatOpenAI(
    #     model=OPENAI_MODEL,
    #     temperature=0.0,
    #     base_url=OPENAI_BASE_URL,
    #     api_key=OPENAI_API_KEY,
    # )

    """
    2、传参方式
    """
    # 方式1
    resp = client.invoke("你是谁？")
    # 方式2
    # resp = client.invoke([
    # 	SystemMessage(content="你是一个专业的数学助手"),
    # 	HumanMessage(content="计算1+1")
    # ])
    # 方式3
    # messages_list = [("system","你是一个专业的数学助手"),("user","计算2+2")]
    # resp = client.invoke(messages_list)
    # 方式4
    # messages_list = [{"role":"system","content":"你是一个专业的数学助手"},{"role":"user","content":"计算3+3"}]
    # resp = client.invoke(messages_list)
    print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))

    # print(resp)
    print(resp.content)



"""
3、调用方式
"""
# 异步调用
async def async_main() -> None:
    client = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
    )
    resp = await client.ainvoke("1*2=？")
    print(resp.content)

# 流式调用
def stream_main() -> None:
    client = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
    )
    resp = client.stream("5*5=？")

    # 遍历迭代器对象，打印每个chunk的内容
    for chunk in resp:
        print(chunk.content)

# 批次调用
def batch_main() -> None:
    client = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
    )
    # 调用batch方法，底部通过thread 并行调用模型
    response = client.batch(
        inputs=[
            [HumanMessage("什么是 Langchain")],
            [HumanMessage("Langchain 的核心模块")]
        ]
    )
    # 打印每个问题的回答
    for question_chunk in response:
        print(question_chunk.content)
"""
4、解析结果
"""
def parse_main() -> None:
    client = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
    )
    # pydantic 用于数据校验，数据模型类，一般继承BaseModel，可以限制数据类型和格式
    class Prime(BaseModel):
        prime: list[int] = Field(description="素数")
        count: list[int] = Field(description="小于该素数的素数个数")

    # 输出解析器：给LLM模型设置输出格式
    json_parser = JsonOutputParser(pydantic_object=Prime)

    input_message= [
        ("system", json_parser.get_format_instructions()),
        ("user", "任意生成5个1000-100000之间素数，并标出小于该素数的素数个数")
    ]
    res = client.invoke(input_message)
    print(res.content)
    parsed_res = json_parser.invoke(res)
    print(type(parsed_res))

"""
5、提示词模板
"""
def prompt_template_main() -> None:
    # 使用构造方法实例化提示词模板
    chat_prompt_template = ChatPromptTemplate.from_messages(
        messages=[
            ("system", "你是一个专业的评论员"),
            ("human", "请评价{product}的优缺点，包括{aspect1}和{aspect2}。"),
        ],
    )
    chat_message_list = chat_prompt_template.invoke({"product": "iPhone15", "aspect1": "性能", "aspect2": "外观"})
    client = init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
    )
    resp = client.invoke(chat_message_list)
    print(resp.content)


if __name__ == "__main__":
    # 同步调用
    # main()

    # 异步调用
    # asyncio.run(async_main())

    # 流式调用
    # stream_main()

    # 批次调用
    # batch_main()

    # 返回数据解析
    # parse_main()

    # 提示词模板
    prompt_template_main()