import json
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import dotenv
from langchain.agents import create_agent
from pydantic import BaseModel, Field


dotenv.load_dotenv()




# =========================
# 1) LLMの出力スキーマ（あなたの仕様に対応）
# =========================
class FilterSpec(BaseModel):
    type: Literal["in_fov", "reachable", "robot_side", "front_top_k"] = Field(
        description="フィルタ種別"
    )
    value: Optional[Literal[True, False, "front", "back", "left", "right"]] = Field(
        default=None,
        description="in_fov/reachable は true/false、robot_side は front/back/left/right"
    )
    k: Optional[int] = Field(
        default=None,
        description="front_top_k 用のk（上位k個）"
    )

class OrderBySpec(BaseModel):
    feature: Literal["depth_rank", "right_rank", "front_rank"] = Field(
        description="並べ替えに使う特徴量"
    )
    direction: Literal["asc", "desc"] = Field(
        description="昇順/降順"
    )

class SelectSpec(BaseModel):
    rank: int = Field(
        ge=1,
        description="1-indexed。並べ替え後の何番目を取るか"
    )

class TieBreakerSpec(BaseModel):
    feature: Literal["depth_rank", "right_rank", "front_rank"] = Field(
        description="同順位のときに使う特徴量"
    )
    direction: Literal["asc", "desc"] = Field(
        description="昇順/降順"
    )

# class LLMDecision(BaseModel):
#     reference_frame: Literal["user", "robot"] = Field(
#         description="参照フレーム（user/robot）"
#     )
#     filters: List[FilterSpec] = Field(
#         default_factory=list,
#         description="候補を絞るフィルタ（上から順に適用される想定）"
#     )
#     order_by: OrderBySpec = Field(
#         description="並べ替えルール"
#     )
#     select: SelectSpec = Field(
#         description="並べ替え後の選択"
#     )
#     tie_breaker: Optional[TieBreakerSpec] = Field(
#         default=None,
#         description="同順位解決（任意）"
#     )

# 座標のやつ
class LLMDecision(BaseModel):
    reference_frame: Literal["user", "robot"] = Field(
        description="参照フレーム（user/robot）"
    )

    selections: List[Dict[str, Any]] = Field(
        description="選択されたオブジェクトのリスト"
    )


    # filters: List[FilterSpec] = Field(
    #     default_factory=list,
    #     description="候補を絞るフィルタ（上から順に適用される想定）"
    # )
    # order_by: OrderBySpec = Field(
    #     description="並べ替えルール"
    # )
    # select: SelectSpec = Field(
    #     description="並べ替え後の選択"
    # )
    # tie_breaker: Optional[TieBreakerSpec] = Field(
    #     default=None,
    #     description="同順位解決（任意）"
    # )


# =========================
# Frame判定エージェント用スキーマ
# =========================
class FrameDecision(BaseModel):
    reference_frame: Literal["user", "robot"] = Field(
        description="参照フレーム（user/robot）"
    )
    reasoning: str = Field(
        description="判定理由の簡潔な説明"
    )


# =========================
# 2) system_prompt をファイルから読む
# =========================
SYSTEM_PROMPT_PATH = Path("./LLM_Agent/prompt/system_prompt_cord.txt")
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

# Frame判定用のシンプルなプロンプト
FRAME_CLASSIFIER_PROMPT = """あなたはパートナーロボットの頭脳として、ユーザーの発話から「どちらの視点（参照フレーム）」で話しているかを判定するエージェントです。

ユーザーはあなた（ロボット）を作業パートナーとして扱っています。以下の基準で分類してください：

- "user": ユーザー（話し手）自身の視点、または特定の視点が示唆されない場合
  - キーワード：「私」「僕」「こっち」「俺」「（単に）右/左/手前/奥」
  - 例：「右にあるやつ取って」「こっちの列の」「手前の箱」

- "robot": あなた（ロボット/聞き手）の視点
  - キーワード：「君」「あなた」「そっち」「ロボット」「アーム」
  - 例：「君から見て右の」「そっちにあるやつ」「あなたの左手側の」

判定ルール：
1. 「君」「あなた」「そっち」など、パートナー（聞き手）への言及がある場合は "robot" とする。
2. 「私」「こっち」など、話し手自身への言及がある場合は "user" とする。
3. 視点の主語がない場合（例：「右のやつ」）は、デフォルトで "user"（ユーザー視点）として扱う。

発話のみを入力として受け取り、JSON形式で reference_frame ("user" or "robot") と reason を返してください。
"""

print("===== SySTEM PROMPT =====")
print(SYSTEM_PROMPT)
print("==========")
# =========================
# 3) Agent を作成（response_format で構造化出力）
# =========================
agent = create_agent(
    model=f"openai:{os.getenv('OPENAI_MODEL', 'gpt-5.2')}",
    tools=[],
    response_format=LLMDecision,
    system_prompt=SYSTEM_PROMPT,
)

# Frame判定用の軽量エージェント
frame_classifier_agent = create_agent(
    model=f"openai:{os.getenv('OPENAI_MODEL_LIGHT', 'gpt-4o-mini')}",
    tools=[],
    response_format=FrameDecision,
    system_prompt=FRAME_CLASSIFIER_PROMPT,
)


# =========================
# Frame判定関数
# =========================
def classify_reference_frame(utterance: str) -> FrameDecision:
    """
    発話から参照フレーム（user/robot）を判定する。
    """
    result = frame_classifier_agent.invoke({"messages": [{"role": "user", "content": utterance}]})
    
    if isinstance(result, FrameDecision):
        return result
    
    structured = result.get("structured_response", None)
    if structured is None:
        raise RuntimeError(f"structured_response not found. keys={list(result.keys())}")
    
    if isinstance(structured, dict):
        return FrameDecision(**structured)
    
    if isinstance(structured, FrameDecision):
        return structured
    
    raise RuntimeError(f"Unexpected structured_response type: {type(structured)}")


# =========================
# 4) 呼び出し関数：LLM入力(JSON) -> LLMDecision
# =========================
def decide_selection_rule(llm_input: dict) -> LLMDecision:
    """
    llm_input はサーバが生成した JSON（utterance + objects(features)）をそのまま渡す。
    """
    content = json.dumps(llm_input, ensure_ascii=False)
    result = agent.invoke({"messages": [{"role": "user", "content": content}]})

    # create_agent の実装/バージョン差で返り値が「Pydantic直」 or 「state(dict)」になることがあるため、
    # 両対応にしておくのが安全です。
    if isinstance(result, LLMDecision):
        return result

    # state(dict) 形式の場合（LangChain docsでよく出る形式）
    structured = result.get("structured_response", None)
    if structured is None:
        raise RuntimeError(f"structured_response not found. keys={list(result.keys())}")

    # structured が dict の場合もあるので Pydantic に通す
    if isinstance(structured, dict):
        return LLMDecision(**structured)

    if isinstance(structured, LLMDecision):
        return structured

    raise RuntimeError(f"Unexpected structured_response type: {type(structured)}")



def execute_decision(decision, llm_input):
    frame = decision.reference_frame

    # objects は llm_input["objects"]
    candidates = []
    for obj in llm_input["objects"]:
        oid = obj["id"]
        ff = obj["features"][frame]  # ← dict
        candidates.append((oid, ff))

    # filters
    for f in decision.filters:
        if f.type == "in_fov":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("in_fov") == f.value
            ]
        elif f.type == "reachable":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("reachable") == f.value
            ]
        elif f.type == "robot_side":
            candidates = [
                (o, ff) for o, ff in candidates
                if ff.get("robot_side") == f.value
            ]
        elif f.type == "front_top_k":
            candidates.sort(key=lambda x: x[1]["front_rank"])
            candidates = candidates[: f.k]
        else:
            raise ValueError(f"Unknown filter {f.type}")

        if not candidates:
            raise RuntimeError("No candidates after filter")

    # order_by
    key_fn = lambda x: x[1][decision.order_by.feature]
    candidates.sort(
        key=key_fn,
        reverse=(decision.order_by.direction == "desc")
    )

    # select
    idx = decision.select.rank - 1
    if idx >= len(candidates):
        raise RuntimeError("Rank out of range")

    selected = candidates[idx]

    # tie_breaker
    if decision.tie_breaker:
        same = [c for c in candidates if key_fn(c) == key_fn(selected)]
        if len(same) > 1:
            tb = decision.tie_breaker
            same.sort(
                key=lambda x: x[1][tb.feature],
                reverse=(tb.direction == "desc")
            )
            selected = same[0]

    return selected[0]

# =========================
# 5) テスト実行（例）
# =========================

if __name__ == "__main__":

    print(classify_reference_frame("あなた側のボックスを取ってください。"))
    # with open("test_llm_input.json") as f:
    #     example_llm_input = json.load(f)
    # # print(example_llm_input)
    # # print("==== LLM Input ====")
    # utter = "一番手前にある箱を選んで"
    # llm_input = build_llm_input(utter, example_llm_input)
    # # print(llm_input)
    # decision = decide_selection_rule(llm_input)
    # # print("==== LLM Decision ====")
    # # print(decision.model_dump())
    # selected_object_id = execute_decision(decision, llm_input)
    # print("==== Selected Object ID ====")
    # print(selected_object_id)

