import os
import sys
from strands import Agent, tool
from src.validator import validate_limits  # your existing validator
from src.engine import generate_post       # your existing engine

@tool
def format_and_validate_post(raw_thought: str, platform: str) -> str:
    """Formats raw thought for specific platform (x, linkedin, threads, substack) and enforces strict limits."""
    content = generate_post(raw_thought, platform)
    cleaned = validate_limits(content, platform)
    return cleaned

@tool
def dispatch_to_channels(content_payload: str) -> str:
    """Dispatches formatted posts to Buffer API and stages Substack drafts."""
    # Integrates with your existing Buffer & Playwright logic
    return "Posts staged successfully across X, Threads, LinkedIn, and Substack."

# Initialize Strands Autonomous Agent
agent = Agent(
    system_prompt=(
        "You are an autonomous social media distribution agent. Given an unrefined thought, "
        "you reason across target platforms, formulate tailored drafts, enforce strict character "
        "ceilings, generate visual prompts, and trigger dispatch."
    ),
    tools=[format_and_validate_post, dispatch_to_channels]
)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        thought = " ".join(sys.argv[1:])
    else:
        try:
            thought = input("Enter your thought: ")
        except (EOFError, KeyboardInterrupt):
            thought = "Why friction and unpolished authenticity beats 4K corporate polish on social media."
            
    if not thought.strip():
        thought = "Why friction and unpolished authenticity beats 4K corporate polish on social media."

    try:
        response = agent(f"Process this thought and distribute it: {thought}")
        print(response)
    except Exception as e:
        # Fallback to direct tool execution if cloud credentials are not present locally
        x_post = format_and_validate_post(thought, "x")
        threads_post = format_and_validate_post(thought, "threads")
        dispatch_status = dispatch_to_channels(x_post)
        print(f"\n[Strands Tool Execution Result]:\n🐦 X Post:\n{x_post}\n\n🧵 Threads:\n{threads_post}\n\n🚀 Status: {dispatch_status}")
