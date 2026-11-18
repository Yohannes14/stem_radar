"""Technology Radar and trend velocity REST endpoints."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_automation_service, get_db_session
from app.api.v1.schemas.radar import (
    DomainVelocityItem,
    DomainVelocityResponse,
    HorizonDetail,
    HorizonItem,
    RadarResponse,
)
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/radar", tags=["Tech Radar & Velocity"])

RADAR_DATA = {
    "adopt": HorizonDetail(
        horizon="adopt",
        definition="Technologies with high ROI, verified production stability, and widespread engineering support.",
        items=[
            HorizonItem(
                technology="LLM Orchestration & Vector RAG",
                focus_or_standard="Qdrant, Chroma, LlamaIndex, pgvector",
                verdict="Essential for grounding generative models without catastrophic hallucinations.",
            ),
            HorizonItem(
                technology="PyTorch 2.x & Graph Compilation",
                focus_or_standard="TorchDynamo, TorchInductor, Triton kernels",
                verdict="Standard runtime for model training and high-throughput inference.",
            ),
            HorizonItem(
                technology="FlashAttention-2 & Memory-Efficient Attention",
                focus_or_standard="Tiling algorithms, fused CUDA kernels",
                verdict="Mandatory standard for long-context sequence modeling (>8k tokens).",
            ),
            HorizonItem(
                technology="Rust for Systems & Embedded Firmware",
                focus_or_standard="Memory safety without GC latency overhead",
                verdict="First choice for high-concurrency kernels, robotics controllers, and WASM.",
            ),
        ],
    ),
    "trial": HorizonDetail(
        horizon="trial",
        definition="High-potential technologies validated in labs or pilot projects; ready for POC evaluation.",
        items=[
            HorizonItem(
                technology="Vision-Language-Action (VLA) Robotics Models",
                focus_or_standard="RT-2, OpenVLA, Octo",
                verdict="Direct tokenized control of robotic end-effectors from visual prompts.",
            ),
            HorizonItem(
                technology="Sim-to-Real Reinforcement Learning Locomotion",
                focus_or_standard="Isaac Gym, Domain Randomization, Humanoid Walk Policies",
                verdict="Dynamic balance recovery surpassing classical inverse kinematics.",
            ),
            HorizonItem(
                technology="On-Device Small Language Models (SLMs)",
                focus_or_standard="1B-4B quantized architectures (GGUF, AWQ, EXL2)",
                verdict="Privacy-first, offline, sub-50ms token generation on edge devices.",
            ),
            HorizonItem(
                technology="Neuromorphic Event-Based Sensors",
                focus_or_standard="Dynamic Vision Sensors (DVS), Spiking Neural Networks",
                verdict="Micro-watt power consumption with microsecond temporal resolution.",
            ),
        ],
    ),
    "assess": HorizonDetail(
        horizon="assess",
        definition="Frontier scientific developments and emerging paradigms worth research tracking and prototypes.",
        items=[
            HorizonItem(
                technology="Quantum Error Mitigation & Logical Qubits",
                focus_or_standard="Surface codes, neutral-atom lattices, fault-tolerant gates",
                verdict="Transitioning from NISQ noisy qubits toward physical error suppression.",
            ),
            HorizonItem(
                technology="High-Temperature Superconductivity",
                focus_or_standard="Hydrides under compression, nickelate thin films",
                verdict="Rigorous peer-reviewed laboratory replication phase.",
            ),
            HorizonItem(
                technology="Non-Invasive Brain-Computer Interfaces (BCI)",
                focus_or_standard="High-density EEG, neural speech decoders",
                verdict="Clinical trials and assistive communication systems.",
            ),
            HorizonItem(
                technology="Synthetic Biology Automated Foundries",
                focus_or_standard="High-throughput DNA synthesis, robotic enzymatic optimization",
                verdict="Pilot biomanufacturing scale-up.",
            ),
        ],
    ),
    "hold": HorizonDetail(
        horizon="hold",
        definition="Anti-patterns, deprecated architectures, or speculative hype; proceed with skepticism.",
        items=[
            HorizonItem(
                technology="Monolithic RNNs / LSTMs for Long Context",
                focus_or_standard="Sequential computation bottleneck preventing GPU scaling",
                verdict="Superseded by Transformers and Linear State Space Models (Mamba).",
            ),
            HorizonItem(
                technology="Proprietary Closed Formats without Export",
                focus_or_standard="Vendor lock-in risk",
                verdict="Inability to run local regression testing or independent audits.",
            ),
            HorizonItem(
                technology="Unquantized Massive Models on Edge Devices",
                focus_or_standard="Excessive thermal and battery throttling",
                verdict="Severe memory bandwidth saturation on mobile hardware.",
            ),
            HorizonItem(
                technology="Unverified Hype Claims without Code / Peer Review",
                focus_or_standard="Speculative claims lacking empirical replication",
                verdict="Avoid deploying into enterprise architectures without validated benchmarks.",
            ),
        ],
    ),
}


@router.get(
    "",
    response_model=RadarResponse,
    status_code=status.HTTP_200_OK,
    summary="Get STEM Technology Radar",
    description="Retrieve technologies classified into Adopt, Trial, Assess, and Hold horizons with momentum signals.",
)
async def get_tech_radar(
    horizon: Optional[str] = Query(default=None, description="Filter horizon: adopt, trial, assess, hold"),
    session: AsyncSession = Depends(get_db_session),
    automation: AutomationService = Depends(get_automation_service),
) -> RadarResponse:
    """Retrieve full or filtered Technology Radar with real-time domain momentum."""
    velocities = await automation.calculate_domain_velocity(session=session)

    if horizon and horizon.lower() in RADAR_DATA:
        filtered_horizons = {horizon.lower(): RADAR_DATA[horizon.lower()]}
    else:
        filtered_horizons = RADAR_DATA

    return RadarResponse(
        horizons=filtered_horizons,
        domain_velocities=velocities,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/velocity",
    response_model=DomainVelocityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Domain Trend Velocity Metrics",
    description="Retrieve evidence-based momentum and publication velocity metrics across STEM domains.",
)
async def get_domain_velocity(
    session: AsyncSession = Depends(get_db_session),
    automation: AutomationService = Depends(get_automation_service),
) -> DomainVelocityResponse:
    """Retrieve domain publication velocity and momentum indicators."""
    velocities = await automation.calculate_domain_velocity(session=session)

    domain_items = []
    for slug, d in velocities.items():
        domain_items.append(
            DomainVelocityItem(
                slug=slug,
                name=d.get("name", slug.title()),
                count=d.get("count", 0),
                paper_count=d.get("paper_count", 0),
                avg_score=d.get("avg_score", 0.0),
                momentum=d.get("momentum", "Stable"),
                top_headline=d.get("top_headline", ""),
            )
        )

    return DomainVelocityResponse(
        domains=domain_items,
        total_domains=len(domain_items),
        timestamp=datetime.now(timezone.utc),
    )
