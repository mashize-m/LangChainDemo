# LangChainDemo

LangChain 学习项目，按课程进度组织代码。

## 环境准备

```powershell
# 更新依赖
uv sync 

# 复制 `.env.example` 为 `.env`，填入你的 API Key。

# 设置python解释器路径
① 打开 Settings → Project: 项目名称 → Python Interpreter。
② 点击右侧的 Add Interpreter（添加解释器）。
③ 选择 Add Local Interpreter（添加本地解释器）
④ 点击 截图红色提示框里的蓝色链接 Select existing interpreter（选择现有解释器）/ 或者是点击 圆圈选项 Select existing（选择现有）
⑤ python路径，这里选择 有当前项目名称\.venv 路径下的python.exe 的路径。
```

## 运行示例

```powershell
# 运行整个项目入口
uv run langchaindemo

# 启动命令会根据 pyproject.toml 文件下的：
# [project.scripts]
# langchaindemo = "langchaindemo.main:main"

# 单独运行某个文件
# uv run python -m langchaindemo.lessons.01_hello_llm
```

## 项目目录结构
```
LangChainDemo/
├── .env                          # 敏感配置（不提交）
├── .env.example                  # 配置模板（提交）
├── .gitignore                    # Git 忽略规则
├── .python-version               # Python 版本锁定（已有）
├── README.md                     # 项目说明（已有）
├── pyproject.toml                # 项目配置（已有，需修改）
├── uv.lock                       # 依赖锁文件（已有）
│
├── data/                         # 本地数据（知识库、PDF、txt）
│   └── .gitkeep
│
├── notebooks/                    # Jupyter Notebook（探索性代码）
│   └── .gitkeep
│
└── src/
    └── langchaindemo/
        ├── __init__.py           # 包初始化（已有，需修改）
        ├── main.py               # 应用入口（需新建）
        ├── config.py             # 统一配置（需新建）
        │
        ├── lessons/              # 课程代码（按课号）
        │   ├── __init__.py
        │   ├── lesson01_llm.py
        │   ├── lesson02_rag.py
        │   ├── 03_output_parser.py
        │   ├── 04_chain.py
        │   ├── 05_memory.py
        │   ├── 06_agent.py
        │   └── 07_rag.py
        │
        ├── prompts/              # 可复用提示词模板
        │   ├── __init__.py
        │   └── templates.py
        │
        ├── tools/                # 自定义工具（Agent 用）
        │   ├── __init__.py
        │   └── search.py
        │
        └── utils/                # 通用工具函数
            ├── __init__.py
            └── llm.py            # 统一创建 LLM 实例
```