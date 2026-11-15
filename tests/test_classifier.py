"""Tests for STEM keyword-based classifier."""

from app.processors.classifier import STEMClassifier


def test_classifier_identifies_ai():
    classifier = STEMClassifier()
    text = "OpenAI releases new GPT reasoning model using reinforcement learning"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "ai" in categories or "machine-learning" in categories


def test_classifier_identifies_robotics():
    classifier = STEMClassifier()
    text = "Boston Dynamics reveals new electric humanoid robot with dexterous manipulators"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "robotics" in categories


def test_classifier_identifies_quantum_physics():
    classifier = STEMClassifier()
    text = "CERN researchers measure novel particle physics properties in hadron collider"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "physics" in categories


def test_classifier_fallback_for_unknown():
    classifier = STEMClassifier()
    text = "A simple generic post without specific technical words"
    results = classifier.classify(text, max_categories=2)

    assert len(results) > 0
    assert results[0][0] in ["emerging-tech", "computer-science"]
