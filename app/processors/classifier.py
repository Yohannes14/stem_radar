"""STEM classification engine matching articles to the 19 STEM domains."""

import re
from typing import Dict, List, Tuple

# Comprehensive keyword definitions for the 19 STEM categories
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "ai": [
        "artificial intelligence",
        "ai",
        "llm",
        "large language model",
        "gpt",
        "gemini",
        "claude",
        "neural network",
        "generative ai",
        "deep learning",
        "agent",
        "reasoning model",
        "transformer",
        "diffusion model",
    ],
    "machine-learning": [
        "machine learning",
        "supervised learning",
        "reinforcement learning",
        "deep learning",
        "pytorch",
        "tensorflow",
        "gradient descent",
        "fine-tuning",
        "model weights",
        "dataset",
        "benchmark",
        "overfitting",
    ],
    "robotics": [
        "robot",
        "robotics",
        "humanoid",
        "actuator",
        "kinematics",
        "quadruped",
        "boston dynamics",
        "manipulator",
        "autonomous mobile",
        "slam",
        "ros",
        "ros2",
        "drone",
        "unmanned",
    ],
    "computer-science": [
        "algorithm",
        "data structure",
        "complexity",
        "turing",
        "computational",
        "cryptography",
        "automata",
        "distributed system",
        "concurrency",
        "formal methods",
    ],
    "software-engineering": [
        "software engineering",
        "architecture",
        "microservices",
        "api",
        "database",
        "git",
        "compiler",
        "rust",
        "python",
        "javascript",
        "golang",
        "refactoring",
        "devops",
        "backend",
        "frontend",
        "open source",
    ],
    "cybersecurity": [
        "cybersecurity",
        "vulnerability",
        "malware",
        "ransomware",
        "zero-day",
        "exploit",
        "encryption",
        "firewall",
        "cve",
        "infosec",
        "penetration testing",
        "phishing",
    ],
    "electronics": [
        "semiconductor",
        "transistor",
        "integrated circuit",
        "chip",
        "asic",
        "pcb",
        "fpga",
        "tsmc",
        "nvidia",
        "intel",
        "arm",
        "analog circuit",
        "microelectronics",
        "foundry",
    ],
    "embedded-systems": [
        "embedded system",
        "microcontroller",
        "firmware",
        "esp32",
        "arduino",
        "raspberry pi",
        "cortex-m",
        "bare-metal",
        "rtos",
        "i2c",
        "spi",
        "uart",
        "risc-v",
    ],
    "iot": [
        "internet of things",
        "iot",
        "smart device",
        "sensor network",
        "mqtt",
        "zigbee",
        "matter protocol",
        "connected sensors",
        "smart home",
        "industrial iot",
    ],
    "mechanical-engineering": [
        "mechanical engineering",
        "cad",
        "finite element",
        "fluid dynamics",
        "thermodynamics",
        "gearbox",
        "stress analysis",
        "additive manufacturing",
        "3d printing",
        "structural analysis",
    ],
    "electrical-engineering": [
        "electrical engineering",
        "power grid",
        "high voltage",
        "transformer",
        "inverter",
        "electromagnetism",
        "substation",
        "renewable transmission",
        "signal processing",
    ],
    "biotechnology": [
        "biotechnology",
        "crispr",
        "gene editing",
        "synthetic biology",
        "dna",
        "rna",
        "bioengineering",
        "cellular",
        "protein folding",
        "genomics",
        "mrna",
    ],
    "physics": [
        "physics",
        "quantum",
        "particle physics",
        "cern",
        "hadron",
        "superconductivity",
        "astrophysics",
        "relativity",
        "gravity",
        "fusion energy",
        "tokamak",
        "dark matter",
    ],
    "chemistry": [
        "chemistry",
        "catalyst",
        "polymer",
        "molecule",
        "molecular",
        "nanomaterial",
        "graphene",
        "battery chemistry",
        "lithium-ion",
        "solid-state battery",
        "synthesis",
    ],
    "mathematics": [
        "mathematics",
        "theorem",
        "topology",
        "linear algebra",
        "calculus",
        "differential equations",
        "combinatorics",
        "probability theory",
        "riemann",
        "number theory",
    ],
    "space-technology": [
        "space technology",
        "nasa",
        "spacex",
        "satellite",
        "orbit",
        "rocket",
        "propulsion",
        "artemis",
        "mars rover",
        "iss",
        "payload",
        "lunar",
        "james webb",
    ],
    "renewable-energy": [
        "renewable energy",
        "solar power",
        "photovoltaic",
        "wind turbine",
        "clean energy",
        "hydrogen fuel",
        "grid storage",
        "decarbonization",
        "geothermal",
        "perovskite",
    ],
    "stem-education": [
        "stem education",
        "curriculum",
        "pedagogy",
        "tutorial",
        "student",
        "classroom",
        "teaching tech",
        "coding boot camp",
        "science fair",
        "hands-on project",
    ],
    "emerging-tech": [
        "emerging technology",
        "brain-computer interface",
        "neuralink",
        "quantum computing",
        "superconductor",
        "synthetic meat",
        "metamaterials",
        "ambient computing",
    ],
}


class STEMClassifier:
    """Classifies text into STEM categories using keyword analysis and scoring."""

    def __init__(self) -> None:
        # Precompile regex word patterns for fast lookup
        self._patterns: Dict[str, List[re.Pattern]] = {}
        for cat_slug, keywords in CATEGORY_KEYWORDS.items():
            self._patterns[cat_slug] = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]

    def classify(self, text: str, max_categories: int = 3) -> List[Tuple[str, float]]:
        """Classify given text into STEM category slugs with confidence scores.
        Returns a list of (category_slug, score) tuples sorted by score descending.
        """
        if not text:
            return [("computer-science", 0.5)]

        scores: Dict[str, float] = {}

        for slug, patterns in self._patterns.items():
            match_count = 0
            for pattern in patterns:
                matches = len(pattern.findall(text))
                if matches > 0:
                    match_count += matches

            if match_count > 0:
                # Normalizing score based on keyword hits
                score = min(1.0, 0.4 + (match_count * 0.15))
                scores[slug] = round(score, 2)

        if not scores:
            # Default fallback when general tech
            return [("emerging-tech", 0.5)]

        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_categories[:max_categories]


# Global classifier instance
classifier = STEMClassifier()
