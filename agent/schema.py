from pydantic import BaseModel, Field
from typing import List

class RootCauseAnalysis(BaseModel):
    incident_summary: str = Field(
        description="A concise summary of the primary observed symptoms across all data sources."
    )
    
    evidence_chain: List[str] = Field(
        description="A chronological list of supporting facts found (e.g., ['14:28: Helm upgrade started', '14:32: Readiness probe failed', '14:33: ServiceA 503 storm']).",
        min_length=1
    )
    
    root_cause_component: str = Field(
        description="The primary component identified as the start of the failure chain."
    )
    
    confidence_score: float = Field(
        description="A score between 0.0 and 1.0. If below 0.75, automated remediation is blocked."
    )
    
    require_human_approval: bool = Field(
        description="Set to True if any destructive or configuration-changing actions are proposed."
    )
    
    recommended_action: str = Field(
        description="Human-readable explanation of the fix and why it addresses the root cause."
    )
    
    executable_fix_cmd: str = Field(
        description="The specific shell/kubectl/helm command to resolve the issue."
    )