"""
Prompt management for LLM agents.
"""
from pathlib import Path


# =========================
# Prompt file paths
# =========================
PROMPT_DIR = Path(__file__).parent / "prompt"
SYSTEM_PROMPT_COORDINATE_PATH = PROMPT_DIR / "system_prompt_cord.txt"
SYSTEM_PROMPT_FEATURE_PATH = PROMPT_DIR / "system_prompt.txt"


# =========================
# Load system prompts
# =========================
def load_system_prompt(mode: str = "coordinate") -> str:
    """
    メインシステムプロンプトを読み込む
    
    Args:
        mode: "coordinate" or "feature"
    """
    if mode == "feature":
        prompt_path = SYSTEM_PROMPT_FEATURE_PATH
    else:
        prompt_path = SYSTEM_PROMPT_COORDINATE_PATH
    
    return prompt_path.read_text(encoding="utf-8")


# =========================
# Frame classifier prompt
# =========================
FRAME_CLASSIFIER_PROMPT = """You are the brain of a partner robot, and your task is to determine which perspective (reference frame) the user is speaking from based on their utterance.

The user treats you (the robot) as a work partner. Please classify based on the following criteria:

- "user": The user's (speaker's) own perspective, or when no specific perspective is indicated
  - Keywords: "I", "me", "my side", "over here", "(simply) right/left/front/back"
  - Examples: "Get the one on the right", "The one in this row", "The box in front"

- "robot": Your (robot/listener's) perspective
  - Keywords: "you", "your", "over there", "robot", "arm"
  - Examples: "The one on your right", "The one over there", "On your left side"

Classification Rules:
1. If there is a reference to the partner (listener) such as "you", "your", "over there", classify as "robot".
2. If there is a reference to the speaker themselves such as "I", "my side", classify as "user".
3. If there is no subject indicating perspective (e.g., "the one on the right"), default to "user" (user's perspective).

Receive only the utterance as input and return the reference_frame ("user" or "robot") and reason in JSON format.
"""
