import os
from pathlib import Path
from dotenv import load_dotenv

# 从 config.py 往上找到项目根目录
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


# 智普
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
# mineru API TOKEN
MINERU_TOKEN = os.getenv("MINERU_TOKEN")

# tivily api key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


