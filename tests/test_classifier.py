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


def test_classifier_identifies_ethiopia_tech():
    classifier = STEMClassifier()
    text = "Telebirr and Safaricom Ethiopia expand mobile money and digital fintech payments in Addis Ababa"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "ethiopia-tech" in categories


def test_classifier_identifies_ethiopian_affairs():
    classifier = STEMClassifier()
    text = "Ethiopian Parliament convenes in Addis Ababa to discuss African Union diplomacy and peace agreement"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "ethiopia-affairs" in categories


def test_classifier_identifies_global_politics():
    classifier = STEMClassifier()
    text = "United Nations Security Council holds urgent multilateral talks on treaty sanctions and global diplomacy"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "global-politics" in categories


def test_classifier_identifies_tech_policy():
    classifier = STEMClassifier()
    text = "Lawmakers propose new tech regulation for algorithmic accountability, AI safety, and digital sovereignty"
    results = classifier.classify(text, max_categories=2)

    categories = [cat for cat, _ in results]
    assert "tech-policy" in categories
