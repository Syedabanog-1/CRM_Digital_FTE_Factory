"""Agent skills manifest — formal definitions of agent capabilities."""

from pydantic import BaseModel


class SkillDefinition(BaseModel):
    """Definition of a single agent skill."""

    name: str
    description: str
    triggers: list[str]
    inputs: list[str]
    outputs: list[str]
    constraints: list[str]
    mapped_function: str


SKILLS: list[SkillDefinition] = [
    SkillDefinition(
        name="Knowledge Retrieval",
        description="Search product documentation to find relevant information for customer queries",
        triggers=[
            "Customer asks a product question",
            "Customer needs help with a feature",
            "Customer reports an issue that may have a documented solution",
        ],
        inputs=["query (str): The customer's question or search terms", "max_results (int): Maximum results to return (default 5)"],
        outputs=["List of KnowledgeBaseEntry with title, content, and relevance score"],
        constraints=[
            "Only returns content from loaded product documentation",
            "Uses fuzzy text matching (difflib.SequenceMatcher)",
            "Returns empty list for queries with no matches above 0.15 threshold",
            "Maximum 5 results by default",
        ],
        mapped_function="src.services.knowledge_base.KnowledgeBaseService.search",
    ),
    SkillDefinition(
        name="Sentiment Analysis",
        description="Analyze customer message sentiment using keyword-based heuristics to detect emotional state",
        triggers=[
            "Every inbound customer message",
            "Before escalation decision",
            "Before closing a conversation (guardrail check)",
        ],
        inputs=["message (str): The customer's message text"],
        outputs=["score (float): 0.0 (negative) to 1.0 (positive)", "label (str): negative, neutral, or positive"],
        constraints=[
            "Keyword-based only — no ML model",
            "Score weights: positive +0.1, negative -0.1, profanity -0.3, legal -0.5",
            "Base score is 0.5 (neutral)",
            "Score clamped to [0.0, 1.0]",
            "Empty messages return 0.5 (neutral)",
            "Escalation triggered when score < 0.3",
        ],
        mapped_function="src.services.sentiment_analyzer.SentimentAnalyzer.analyze",
    ),
    SkillDefinition(
        name="Escalation Decision",
        description="Determine whether a customer message requires human intervention based on multiple trigger categories",
        triggers=[
            "Every inbound customer message is checked",
            "After failed knowledge base searches (2+ failures)",
            "When sentiment drops below threshold",
        ],
        inputs=[
            "message (str): The customer's message",
            "sentiment_score (float, optional): Pre-computed sentiment",
            "failed_kb_searches (int): Count of consecutive failed KB searches",
        ],
        outputs=["EscalationResult with should_escalate (bool), reason (str), guardrail_triggered (bool)"],
        constraints=[
            "Non-negotiable triggers: legal threats, pricing/billing, profanity, explicit human requests",
            "Sentiment threshold: 0.3",
            "Knowledge gap: 2 consecutive failed searches",
            "Competitor mentions trigger guardrail flag",
            "Must never answer directly for escalation-worthy queries",
        ],
        mapped_function="src.services.escalation_engine.EscalationEngine.check",
    ),
    SkillDefinition(
        name="Channel Adaptation",
        description="Format agent responses appropriately for the target communication channel",
        triggers=[
            "Every outbound agent response",
            "When channel is specified in message metadata",
        ],
        inputs=[
            "message (str): Raw response content",
            "channel (Channel): email, whatsapp, or web_form",
            "customer_name (str, optional): For personalized greetings",
            "ticket_id (str, optional): For reference in email signatures",
        ],
        outputs=["formatted_response (str): Channel-appropriate formatted text"],
        constraints=[
            "Email: formal greeting, body, signature, ticket ref. Max 500 words.",
            "WhatsApp: no greeting, concise body. Max 300 chars preferred, 1600 absolute.",
            "Web Form: brief greeting, body, next-steps footer. Max 300 words.",
            "Long messages truncated with '...' indicator",
            "No emojis in email responses",
        ],
        mapped_function="src.services.channel_formatter.ChannelFormatter.format",
    ),
    SkillDefinition(
        name="Customer Identification",
        description="Resolve customer identity across channels using email as primary and phone as secondary identifier",
        triggers=[
            "First message from a customer in a session",
            "When customer contacts from a new channel",
            "When phone number needs to be linked to email",
        ],
        inputs=[
            "email (str, optional): Customer email address (primary identifier)",
            "phone (str, optional): Customer phone number (secondary identifier)",
            "name (str, optional): Customer display name",
        ],
        outputs=["Customer: resolved or newly created customer record"],
        constraints=[
            "Email is the primary identifier (unique, required for creation)",
            "Phone mapped via CustomerIdentifier table",
            "New customers auto-created when email is unknown",
            "Case-insensitive email matching",
            "Phone must include country code prefix (+)",
        ],
        mapped_function="src.services.customer_resolver.CustomerResolver.resolve",
    ),
]


def get_skills() -> list[SkillDefinition]:
    """Return all defined skills."""
    return SKILLS


def validate_skills() -> dict[str, bool]:
    """Validate that each skill's mapped function exists and is importable."""
    results = {}
    for skill in SKILLS:
        module_path, func_name = skill.mapped_function.rsplit(".", 1)
        try:
            import importlib
            parts = module_path.split(".")
            # Handle class methods: module.Class.method
            if len(parts) >= 3 and parts[-1][0].isupper():
                mod = importlib.import_module(".".join(parts[:-1]))
                cls = getattr(mod, parts[-1])
                func = getattr(cls, func_name, None)
            else:
                mod = importlib.import_module(module_path)
                func = getattr(mod, func_name, None)
            results[skill.name] = func is not None
        except (ImportError, AttributeError):
            results[skill.name] = False
    return results
