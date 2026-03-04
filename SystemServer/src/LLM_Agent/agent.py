"""
LLM Agent - Main entry point and CLI for testing.

This module provides backward compatibility and serves as a test entry point.
For new code, import directly from the LLM_Agent package:

    from LLM_Agent import classify_reference_frame, decide_selection_rule
"""
import json
import sys
from pathlib import Path

# Add parent to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Re-export all public APIs for backward compatibility
from .schemas import (
    FilterSpec,
    OrderBySpec,
    SelectSpec,
    TieBreakerSpec,
    LLMDecision,
    FrameDecision,
)
from .core import (
    classify_reference_frame,
    decide_selection_rule,
    execute_decision,
)
from .agents import (
    get_selection_agent,
    get_frame_classifier_agent,
)


# =========================
# Test execution
# =========================
if __name__ == "__main__":
    print("=== LLM Agent Test ===\n")
    
    # Test frame classification
    test_utterance = "あなた側のボックスを取ってください。"
    print(f"Test utterance: {test_utterance}")
    result = classify_reference_frame(test_utterance)
    print(f"Frame: {result.reference_frame}")
    print(f"Reasoning: {result.reasoning}")
    
    # Uncomment to test selection
    # with open("test_llm_input.json") as f:
    #     example_llm_input = json.load(f)
    # utter = "一番手前にある箱を選んで"
    # decision = decide_selection_rule(example_llm_input)
    # print(f"Decision: {decision.model_dump()}")

