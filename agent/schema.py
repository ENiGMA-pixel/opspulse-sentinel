from pydantic import BaseModel, Field
from typing import List


class RootCauseAnalysis(BaseModel):
    incident_summary: str = Field(
        description="Concise summary of observed symptoms across all data sources."
    )
    evidence_chain: List[str] = Field(
        description="Chronological list of supporting events leading to the root cause.",
        min_length=1
    )
    root_cause_component: str = Field(
        description="The component identified as the origin of the failure chain."
    )
    confidence_score: float = Field(
        description="Confidence in this RCA from 0.0 to 1.0. Below 0.75 blocks automated remediation."
    )
    require_human_approval: bool = Field(
        description="True if the proposed fix modifies production infrastructure."
    )
    recommended_action: str = Field(
        description="Plain english explanation of the fix and why it resolves the root cause."
    )
    executable_fix_cmd: str = Field(
        description="Exact shell, kubectl, or helm command to execute the fix."
    )