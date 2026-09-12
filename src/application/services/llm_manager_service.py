import requests
import json
from typing import Dict, Any, List, Optional
from src.config.settings import settings
from src.application.services.system_telemetry_service import telemetry_service


class LLMManagerService:
    """
    Serviço para monitoramento, controle de ciclo de vida e gerenciamento
    de VRAM do Ollama e provedores de LLM.
    """
    def __init__(self, ollama_host: Optional[str] = None):
        self.ollama_host = ollama_host or getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.llm_enabled = True
        self.active_provider = getattr(settings, "LLM_PROVIDER", "ollama")
        self.active_model = getattr(settings, "OLLAMA_LLM_MODEL", "qwen2.5-coder:32b")
        self.temperature = 0.2

    def get_status(self) -> Dict[str, Any]:
        """Verifica o status operacional do Ollama, modelos carregados em VRAM e modelos disponíveis."""
        ollama_online = False
        available_models = []
        loaded_models = []

        try:
            # Consulta modelos instalados
            res_tags = requests.get(f"{self.ollama_host}/api/tags", timeout=1.5)
            if res_tags.status_code == 200:
                ollama_online = True
                data = res_tags.json()
                for m in data.get("models", []):
                    details = m.get("details", {})
                    available_models.append({
                        "name": m.get("name"),
                        "size": m.get("size", 0),
                        "parameter_size": details.get("parameter_size", "N/A"),
                        "quantization": details.get("quantization_level", "N/A"),
                        "family": details.get("family", "N/A")
                    })

            # Consulta modelos carregados na VRAM
            if ollama_online:
                res_ps = requests.get(f"{self.ollama_host}/api/ps", timeout=1.5)
                if res_ps.status_code == 200:
                    data_ps = res_ps.json()
                    for m in data_ps.get("models", []):
                        loaded_models.append({
                            "name": m.get("name"),
                            "size_vram": m.get("size_vram", m.get("size", 0)),
                            "expires_at": m.get("expires_at")
                        })
        except Exception:
            ollama_online = False

        return {
            "llm_enabled": self.llm_enabled,
            "active_provider": self.active_provider,
            "active_model": self.active_model,
            "temperature": self.temperature,
            "ollama_online": ollama_online,
            "ollama_host": self.ollama_host,
            "available_models": available_models,
            "loaded_models_vram": loaded_models,
            "has_loaded_vram": len(loaded_models) > 0
        }

    def toggle_llm_state(self, enabled: bool) -> Dict[str, Any]:
        """Liga ou desliga o uso de LLM (quando False, as consultas funcionam no modo Context-Only / Bypass)."""
        self.llm_enabled = enabled
        status_str = "LIGADO (Inferência Ativa)" if enabled else "DESLIGADO (Modo Contexto Enxuto / Bypass)"
        telemetry_service.log(
            level="INFO",
            module="LLMManager",
            message=f"Estado do LLM alterado para: {status_str}"
        )
        return self.get_status()

    def set_config(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Atualiza a configuração ativa de LLM."""
        if provider is not None:
            self.active_provider = provider
        if model is not None:
            self.active_model = model
        if temperature is not None:
            self.temperature = temperature
        if enabled is not None:
            self.llm_enabled = enabled

        telemetry_service.log(
            level="INFO",
            module="LLMManager",
            message=f"Configurações de LLM atualizadas: Provedor={self.active_provider}, Modelo={self.active_model}, Temp={self.temperature}, Ativo={self.llm_enabled}"
        )
        return self.get_status()

    def unload_vram(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Descarrega modelos da VRAM do Ollama enviando keep_alive=0,
        liberando 100% da memória da GPU imediatamente.
        """
        target = model_name or self.active_model
        try:
            res = requests.post(
                f"{self.ollama_host}/api/generate",
                json={"model": target, "keep_alive": 0},
                timeout=5.0
            )
            telemetry_service.log(
                level="INFO",
                module="LLMManager",
                message=f"VRAM liberada com sucesso para o modelo '{target}'."
            )
            return {"success": True, "message": f"Modelo '{target}' descarregado da GPU/VRAM.", "status": self.get_status()}
        except Exception as e:
            telemetry_service.log(
                level="ERROR",
                module="LLMManager",
                message=f"Erro ao descarregar VRAM de '{target}': {str(e)}"
            )
            return {"success": False, "message": str(e), "status": self.get_status()}


llm_manager_service = LLMManagerService()
