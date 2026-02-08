"""Keyword-based sentiment analysis service."""

import re


class SentimentAnalyzer:
    """Analyzes message sentiment using keyword-based heuristics."""

    POSITIVE_WORDS = {
        "thank", "thanks", "great", "wonderful", "excellent", "amazing",
        "awesome", "fantastic", "love", "appreciate", "helpful", "perfect",
        "brilliant", "outstanding", "pleased", "happy", "satisfied",
        "impressive", "good", "nice", "well",
    }

    NEGATIVE_WORDS = {
        "bad", "poor", "terrible", "awful", "horrible", "frustrating",
        "annoying", "disappointing", "slow", "broken", "fail", "failed",
        "wrong", "error", "issue", "problem", "hate", "angry", "upset",
        "confused", "difficult", "complicated", "worst",
    }

    PROFANITY_WORDS = {
        "damn", "hell", "crap", "garbage", "useless", "stupid",
        "idiot", "ridiculous", "pathetic", "incompetent", "scam",
    }

    LEGAL_WORDS = {
        "lawyer", "attorney", "lawsuit", "sue", "legal", "court",
        "litigation",
    }

    # Weights per category
    POSITIVE_WEIGHT = 0.1
    NEGATIVE_WEIGHT = -0.1
    PROFANITY_WEIGHT = -0.3
    LEGAL_WEIGHT = -0.5

    BASE_SCORE = 0.5  # neutral starting point

    def analyze(self, message: str) -> float:
        """Analyze sentiment and return score from 0.0 (negative) to 1.0 (positive)."""
        if not message or not message.strip():
            return self.BASE_SCORE

        words = set(re.findall(r"[a-zA-Z]{3,}", message.lower()))

        score = self.BASE_SCORE

        # Positive words
        positive_matches = words & self.POSITIVE_WORDS
        score += len(positive_matches) * self.POSITIVE_WEIGHT

        # Negative words
        negative_matches = words & self.NEGATIVE_WORDS
        score += len(negative_matches) * self.NEGATIVE_WEIGHT

        # Profanity (steep drop)
        profanity_matches = words & self.PROFANITY_WORDS
        score += len(profanity_matches) * self.PROFANITY_WEIGHT

        # Legal terms (steepest drop)
        legal_matches = words & self.LEGAL_WORDS
        score += len(legal_matches) * self.LEGAL_WEIGHT

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))

    def get_label(self, score: float) -> str:
        """Get human-readable label for a sentiment score."""
        if score >= 0.6:
            return "positive"
        elif score <= 0.4:
            return "negative"
        return "neutral"
