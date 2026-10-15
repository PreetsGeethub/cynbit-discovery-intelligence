
from typing import Literal

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    value: str | None = None
    evidence: list[str] = Field(default_factory=list)
    status: Literal["stated", "unknown"] = "unknown"


class DiscoveryQuestion(BaseModel):
    question: str
    priority: Literal["high", "medium", "low"]


class DiscoveryExtraction(BaseModel):
    project_goal: Requirement
    target_users: Requirement
    integrations: Requirement
    timeline: Requirement
    budget: Requirement
    security_requirements: Requirement
    missing_information: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    discovery_questions: list[DiscoveryQuestion] = Field(
        default_factory=list
    )
