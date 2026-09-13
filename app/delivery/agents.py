"""
Información sobre los agentes (tutores) disponibles.
"""

from fastapi import APIRouter, HTTPException

from app.domain.agents import AGENTS

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("")
def list_agents():
    return [
        {
            "name": cfg["name"],
            "table": cfg["table"],
            "model_id": f"chatpdep-{cfg['name'].lower()}",
        }
        for cfg in AGENTS.values()
    ]


@router.get("/{agent_name}")
def get_agent(agent_name: str):
    cfg = AGENTS.get(agent_name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_name}' no encontrado.")
    return {
        "name": cfg["name"],
        "table": cfg["table"],
        "model_id": f"chatpdep-{cfg['name'].lower()}",
    }
