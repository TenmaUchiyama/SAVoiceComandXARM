import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

# `.env` を読み込んで環境変数へ反映
load_dotenv()

app = FastAPI()


class LLMRequest(BaseModel):
    text: str


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """
    LangChain(OpenAI) の LLM を初期化して返す。
    - OPENAI_API_KEY: 必須（.env でもOK）
    - OPENAI_MODEL: 任意（デフォルト: gpt-4o-mini）
    - OPENAI_TEMPERATURE: 任意（デフォルト: 0）
    """

    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    try:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0"))
    except ValueError:
        temperature = 0.0

    return ChatOpenAI(
        model=model,
        temperature=temperature
    )


@app.get("/")
async def root():
    """エントリポイント: Hello World"""
    return {"message": "Hello World"}


@app.post("/llm")
async def llm_endpoint(request: LLMRequest):
    """エントリポイント: 文字列を受け取り LLM 推論して返す"""
    try:
        llm = get_llm()
        response = llm.invoke([HumanMessage(content=request.text)])
        return {"input": request.text, "output": response.content}
    except RuntimeError as e:
        # 設定不備系（APIキーなど）
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM推論エラー: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
