
"""
LangGraph interrupt 演示：转账前的人工审核
"""

from typing import Any
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


# 1. 定义状态
class TransferState(TypedDict):
    recipient: str #收款人
    amount: int #转账金额
    memo: str  #备注
    approved: bool  #审核是否通过    True允许转账    False拒绝转账
    final_status: str   #最终状态     转账成功或失败的状态


# 2. 定义节点
def review_transfer(state: TransferState) -> dict[str, Any]:
    """
    审核节点：生成待审核信息，并调用 interrupt 暂停
    """
    print("\n[Node] review_transfer：生成待执行的转账请求")

    # 准备待审核的数据
    pending_transfer = {
        "recipient": state["recipient"],
        "amount": state["amount"],
        "memo": state["memo"],
    }

    # --- 触发中断 ---
    # 程序会在这里暂停，并将 value 中的数据返回给调用者
    user_review = interrupt(
        {
            "title": "转账审核",
            "pending_transfer": pending_transfer,
            "instruction": "请返回 bool(是否批准) 或 dict(修改字段)",
        }
    )
    # ----------------

    # 处理用户返回的决策
    approved = False
    updated_transfer = dict(pending_transfer)

    if isinstance(user_review, bool):
        approved = user_review
    elif isinstance(user_review, dict):
        approved = bool(user_review.get("approved", True))
        # 更新用户修改的字段
        for k in ("recipient", "amount", "memo"):
            if k in user_review:
                updated_transfer[k] = user_review[k]

    print(f"[Node] review_transfer：用户决策 approved={approved}")

    return {
        "approved": approved,
        "recipient": updated_transfer["recipient"],
        "amount": updated_transfer["amount"],
        "memo": updated_transfer["memo"],
    }


def execute_transfer(state: TransferState) -> dict[str, str]:
    """
    执行节点：根据审核结果执行转账
    """
    if not state["approved"]:
        print("\n[Node] execute_transfer：用户未批准，取消转账")
        return {"final_status": "已取消：用户未批准"}

    print("\n[Node] execute_transfer：模拟执行转账...")
    return {
        "final_status": f"成功转账 {state['amount']} 元给 {state['recipient']}"
    }


# 3. 构建图
def build_graph():
    # 必须传入 checkpointer 才能支持中断
    graph = StateGraph(TransferState)
    graph.add_node("review_transfer", review_transfer)
    graph.add_node("execute_transfer", execute_transfer)

    graph.add_edge(START, "review_transfer")
    graph.add_edge("review_transfer", "execute_transfer")
    graph.add_edge("execute_transfer", END)

    return graph.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":

    app = build_graph()
    config = {"configurable": {"thread_id": "transfer-thread-01"}}

    initial_state = {
            "recipient": "Alice",
            "amount": 100,
            "memo": "午餐AA",
            #"approved": False,
            #"final_status": "",
    }

    print("=== 第一次调用：触发中断 ===")
    # 第一次调用，图会在 interrupt 处暂停
    result = app.invoke(initial_state, config=config)

    # 获取中断信息
    interrupt_val = result["__interrupt__"][0]
    print(f"系统暂停，等待审核。待审核数据: {interrupt_val.value}")

    print("\n=== 第二次调用：恢复执行 ===")
    # 模拟用户修改了金额并批准
    user_decision = {"approved": True, "amount": 80, "memo": "实付80元"}

    # 使用 Command(resume=...) 将数据传回图中
    final_result = app.invoke(Command(resume=user_decision), config=config)

    print(f"最终结果: {final_result['final_status']}")