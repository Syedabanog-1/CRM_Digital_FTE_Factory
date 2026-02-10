"""OpenAI Agents SDK Agent definition for the TechCorp Customer Success Agent.

This is the production agent that replaces the Stage 1 MCP server prototype.
Uses gpt-4o model with 6 @function_tool tools and a formalized system prompt.
"""

from agents import Agent

from production.agent.prompts import get_system_prompt
from production.agent.tools import (
    analyze_sentiment,
    create_ticket,
    escalate_to_human,
    get_customer_history,
    search_knowledge_base,
    send_response,
)

# Production agent definition per constitution:
# - Model: gpt-4o (Constitution requirement)
# - 6 tools transformed from Stage 1 MCP tools
# - Formalized system prompt with hard constraints and guardrails
customer_success_agent = Agent(
    name="TechCorp Customer Success Agent",
    model="gpt-4o",
    instructions=get_system_prompt(),
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
        analyze_sentiment,
    ],
)
