"""
Información sobre los agentes (tutores) disponibles.
"""

from fastapi import APIRouter
from config.agents import AGENTS

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("")
def list_agents():
    """Lista todos los agentes disponibles con su información básica."""
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
    """Devuelve la configuración de un agente específico."""
    cfg = AGENTS.get(agent_name)
    if not cfg:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agente '{agent_name}' no encontrado.")
    return {
        "name": cfg["name"],
        "table": cfg["table"],
        "model_id": f"chatpdep-{cfg['name'].lower()}",
    }
