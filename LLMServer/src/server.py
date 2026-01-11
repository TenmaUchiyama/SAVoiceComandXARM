# main.py
from fastapi import FastAPI
from models import CommandRequest, LLMInputContext
from SpatialCalculator import SpatialCalculator

app = FastAPI(title="Spatial Reasoning Adapter", version="1.0")

# Serviceクラスのインスタンス化（Dependency Injection的利用）
# 必要であれば設定値をここで渡せます
calculator = SpatialCalculator(fov_deg=60.0)

@app.post("/command", response_model=LLMInputContext)
async def receive_command(req: CommandRequest):
    """
    Entry point for HoloLens spatial commands.
    Delegates logic to SpatialCalculator.
    """
    # ロジックは全てcalculatorにお任せ
    result = calculator.process_request(req)
    
    # 将来的にここでLLM呼び出しサービスを呼ぶことになる
    # llm_response = llm_service.call(result)
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)