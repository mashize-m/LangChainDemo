
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from langchaindemo.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
import json

"""
生成实例方式
"""
# client = init_chat_model(
# 	model=OPENAI_MODEL,
# 	model_provider="openai",
# )
client = ChatOpenAI(
        model=OPENAI_MODEL,
        temperature=0.0,
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )

"""
调用方式
"""
# 方式1
# resp = client.invoke("你是谁？")
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


"""
交互方式
"""


print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))

# print(resp)
print(resp.content)

