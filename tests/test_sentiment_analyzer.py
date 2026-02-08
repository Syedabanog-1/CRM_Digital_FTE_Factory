"""Tests for US3: Sentiment analyzer service."""

import pytest
from src.services.sentiment_analyzer import SentimentAnalyzer


@pytest.fixture
def analyzer():
    return SentimentAnalyzer()


class TestPositiveSentiment:
    def test_positive_words_high_score(self, analyzer):
        score = analyzer.analyze("Thank you so much, this is great and wonderful!")
        assert score > 0.6

    def test_gratitude_is_positive(self, analyzer):
        score = analyzer.analyze("Thanks for the quick help, really appreciate it")
        assert score > 0.5


class TestNegativeSentiment:
    def test_negative_words_low_score(self, analyzer):
        score = analyzer.analyze("This is terrible and frustrating, very disappointing")
        assert score < 0.4

    def test_profanity_steep_drop(self, analyzer):
        score = analyzer.analyze("This damn product is garbage")
        assert score < 0.3

    def test_legal_terms_steep_drop(self, analyzer):
        score = analyzer.analyze("I will contact my lawyer about this lawsuit")
        assert score < 0.3


class TestNeutralSentiment:
    def test_neutral_message(self, analyzer):
        score = analyzer.analyze("How do I create a new project?")
        assert 0.35 <= score <= 0.65

    def test_empty_message_neutral(self, analyzer):
        score = analyzer.analyze("")
        assert score == 0.5

    def test_emoji_only_neutral(self, analyzer):
        score = analyzer.analyze("👍👍👍")
        assert 0.4 <= score <= 0.6


class TestScoreRange:
    def test_score_between_0_and_1(self, analyzer):
        for msg in ["hate hate hate", "love love love", "hello", ""]:
            score = analyzer.analyze(msg)
            assert 0.0 <= score <= 1.0

    def test_threshold_crossing(self, analyzer):
        mild = analyzer.analyze("This is a bit annoying")
        severe = analyzer.analyze("This is terrible awful garbage useless damn")
        assert severe < mild
