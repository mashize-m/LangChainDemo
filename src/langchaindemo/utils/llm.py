# from langchain_openai import ChatOpenAI

from openai import OpenAI
from langchaindemo.config import (
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
    ZHIPU_MODEL,
)
import json

client = OpenAI(
	base_url=ZHIPU_BASE_URL, # 平台提供的 URL,默认可省略
	api_key=ZHIPU_API_KEY, # 平台提供的 API-Key,默认可省略
)
resp = client.chat.completions.create(
	model=ZHIPU_MODEL, # 模型名称
	messages=[{"role": "user", "content": "将'你好'翻译成英语"}], # 用户输入
)

print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))

print(resp.choices[0].message.content)


# def get_llm():
#     """返回一个配置好的 DeepSeek LLM 实例。"""
#     return ChatOpenAI(
#         api_key=ZHIPU_API_KEY,
#         base_url=ZHIPU_BASE_URL,
#     )