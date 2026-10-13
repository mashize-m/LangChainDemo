from langchain_core.prompts import ChatPromptTemplate

# 示例：翻译提示词
TRANSLATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业翻译，把用户输入翻译成{target_language}。"),
    ("human", "{text}"),
])