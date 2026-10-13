from langchaindemo.utils.llm import get_llm


def main() -> None:
    llm = get_llm()
    response = llm.invoke("你好，请用一句话介绍你自己。")
    print(response.content)


if __name__ == "__main__":
    main()