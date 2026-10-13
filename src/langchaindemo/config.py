import os
from pathlib import Path
from dotenv import load_dotenv

# 从 config.py 往上找到项目根目录
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# 智普
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL")

