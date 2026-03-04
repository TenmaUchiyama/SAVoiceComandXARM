"""
LLM Agent factory and instances.
"""
import os
import dotenv
from langchain.agents import create_agent

from .schemas import LLMDecisionCoordinate, LLMDecisionFeature, FrameDecision
from .prompts import load_system_prompt, FRAME_CLASSIFIER_PROMPT


# Load environment variables
dotenv.load_dotenv()


def get_llm_input_mode() -> str:
    """Get current LLM input mode from environment."""
    mode = os.getenv("LLM_INPUT_MODE", "coordinate").lower()
    return mode if mode in ["coordinate", "feature"] else "coordinate"


def _get_model_string(heavy: bool = True) -> str:
    """
    Get model string based on provider configuration.
    
    Supported providers:
        - openai: gpt-4o, gpt-4o-mini
        - google-genai: gemini-2.0-flash-exp, gemini-1.5-flash
        - anthropic: claude-3-5-sonnet-20241022
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "google-genai" or provider == "gemini":
        model = os.getenv("GOOGLE_MODEL" if heavy else "GOOGLE_MODEL_LIGHT", 
                         "gemini-2.0-flash-exp" if heavy else "gemini-1.5-flash")
        return f"google-genai:{model}"
    
    elif provider == "anthropic" or provider == "claude":
        model = os.getenv("ANTHROPIC_MODEL" if heavy else "ANTHROPIC_MODEL_LIGHT",
                         "claude-3-5-sonnet-20241022" if heavy else "claude-3-5-haiku-20241022")
        return f"anthropic:{model}"
    
    else:  # default to openai
        model = os.getenv("OPENAI_MODEL" if heavy else "OPENAI_MODEL_LIGHT",
                         "gpt-4o" if heavy else "gpt-4o-mini")
        return f"openai:{model}"


def create_selection_agent():
    """メインの選択エージェントを作成"""
    mode = get_llm_input_mode()
    system_prompt = load_system_prompt(mode=mode)
    
    # Choose response schema based on mode
    response_format = LLMDecisionCoordinate if mode == "coordinate" else LLMDecisionFeature
    
    model_string = _get_model_string(heavy=True)
    print("===== SYSTEM PROMPT =====")
    print(system_prompt)
    print(f"===== MODEL: {model_string} =====")
    print(f"===== INPUT MODE: {mode} =====")
    
    return create_agent(
        model=model_string,
        tools=[],
        response_format=response_format,
        system_prompt=system_prompt,
    )


def create_frame_classifier_agent():
    """参照フレーム判定用の軽量エージェントを作成"""
    model_string = _get_model_string(heavy=False)
    return create_agent(
        model=model_string,
        tools=[],
        response_format=FrameDecision,
        system_prompt=FRAME_CLASSIFIER_PROMPT,
    )


# =========================
# Singleton agent instances
# =========================
_selection_agent = None
_frame_classifier_agent = None


def get_selection_agent():
    """選択エージェントのシングルトンインスタンスを取得"""
    global _selection_agent
    if _selection_agent is None:
        _selection_agent = create_selection_agent()
    return _selection_agent


def get_frame_classifier_agent():
    """フレーム判定エージェントのシングルトンインスタンスを取得"""
    global _frame_classifier_agent
    if _frame_classifier_agent is None:
        _frame_classifier_agent = create_frame_classifier_agent()
    return _frame_classifier_agent
