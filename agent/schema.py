from pydantic import BaseModel, Field

class RootCauseAnalysis(BaseModel):
    incident_summary: str = Field(
        description="A one-sentence summary of the observed symptoms (e.g., '503 errors on ServiceA')."
    )
    root_cause_component: str = Field(
        description="The specific component that caused the failure (e.g., 'ingress-controller')."
    )
    confidence_score: float = Field(
        description="A score between 0.0 and 1.0 indicating confidence in this RCA. If below 0.75, escalate."
    )
    require_human_approval: bool = Field(
        description="MUST be True if the recommended action involves modifying production infrastructure."
    )
    recommended_action: str = Field(
        description="Plain english explanation of how to fix the issue."
    )
    executable_fix_cmd: str = Field(
        description="The exact terminal or kubectl command to execute the fix."
    )