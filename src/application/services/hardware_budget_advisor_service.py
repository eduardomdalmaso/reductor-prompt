import os
import shutil
import logging
from typing import Dict, Any, Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


class HardwareBudgetAdvisorService:
    """
    Serviço que inspeciona o hardware local (GPU/VRAM) e o provedor LLM configurado,
    gerando orientações dinâmicas de parâmetros para agentes de IA e desenvolvedores.
    """

    def detect_hardware(self) -> Dict[str, Any]:
        """Detecta GPUs NVIDIA disponíveis ou faz fallback para CPU."""
        gpu_info = {
            "has_gpu": False,
            "device_name": "CPU",
            "total_vram_gb": 0.0,
            "free_vram_gb": 0.0,
            "vram_tier": "NONE"
        }

        # 1. Tenta via PyTorch CUDA se instalado
        try:
            import torch
            if torch.cuda.is_available():
                device_idx = 0
                dev_name = torch.cuda.get_device_name(device_idx)
                total_mem = torch.cuda.get_device_properties(device_idx).total_memory / (1024 ** 3)
                free_mem = (torch.cuda.mem_get_info()[0] / (1024 ** 3)) if hasattr(torch.cuda, "mem_get_info") else total_mem * 0.8
                
                gpu_info["has_gpu"] = True
                gpu_info["device_name"] = dev_name
                gpu_info["total_vram_gb"] = round(total_mem, 1)
                gpu_info["free_vram_gb"] = round(free_mem, 1)
        except Exception:
            pass

        # 2. Fallback via nvidia-smi se torch não detectou
        if not gpu_info["has_gpu"] and shutil.which("nvidia-smi"):
            try:
                import subprocess
                cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"]
                out = subprocess.check_output(cmd, encoding="utf-8").strip()
                if out:
                    first_gpu = out.split("\n")[0].split(",")
                    name = first_gpu[0].strip()
                    total_mb = float(first_gpu[1].strip())
                    free_mb = float(first_gpu[2].strip())
                    
                    gpu_info["has_gpu"] = True
                    gpu_info["device_name"] = name
                    gpu_info["total_vram_gb"] = round(total_mb / 1024, 1)
                    gpu_info["free_vram_gb"] = round(free_mb / 1024, 1)
            except Exception:
                pass

        # Classificação por faixa de VRAM (Tier)
        vram = gpu_info["total_vram_gb"]
        if vram >= 24.0:
            gpu_info["vram_tier"] = "ULTRA"  # RTX 5090, 4090, 3090, A6000 (24GB a 48GB)
        elif vram >= 12.0:
            gpu_info["vram_tier"] = "MID"    # RTX 4070, 3060 12GB (12GB a 16GB)
        elif vram >= 6.0:
            gpu_info["vram_tier"] = "ENTRY"  # RTX 3060 6GB, 4050/4060 8GB
        else:
            gpu_info["vram_tier"] = "CPU"

        return gpu_info

    def get_runtime_advice(self, provider_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera conselho arquitetural e parâmetros ótimos com base no hardware e modelo ativo.
        """
        hardware = self.detect_hardware()
        provider = (provider_override or settings.LLM_PROVIDER or "ollama").lower()
        gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

        # ==========================================
        # 1. Provedor Local: Ollama (GPU / VRAM Própria)
        # ==========================================
        if provider == "ollama":
            vram_tier = hardware["vram_tier"]
            
            if vram_tier == "ULTRA":
                return {
                    "runtime_environment": "LOCAL_GPU_ABUNDANT",
                    "hardware_detected": f"{hardware['device_name']} ({hardware['total_vram_gb']}GB VRAM)",
                    "financial_cost": "R$ 0,00 (Totalmente Local e Ilimitado)",
                    "active_provider": "ollama",
                    "recommended_model": "qwen2.5:32b ou qwen2.5:14b",
                    "optimal_parameters": {
                        "max_tokens": 5000,
                        "use_local_llm": True,
                        "deep_reasoning": True,
                        "enable_rewriting": True,
                        "query_expansion_variations": 4,
                        "use_brain": True
                    },
                    "strategy_name": "Deep Reasoning & High-Capacity Context",
                    "guidance_for_agent": (
                        "Você está rodando em hardware local de altíssimo desempenho (VRAM >= 24GB). "
                        "Não há limites financeiros ou de tokens de entrada. "
                        "Pode utilizar `--deep` (Chain-of-Thought profundo), expansão de 4 queries "
                        "e extrair até 5.000 tokens de contexto para máxima precisão e zero alucinação."
                    )
                }

            elif vram_tier == "MID":
                return {
                    "runtime_environment": "LOCAL_GPU_MODERATE",
                    "hardware_detected": f"{hardware['device_name']} ({hardware['total_vram_gb']}GB VRAM)",
                    "financial_cost": "R$ 0,00 (Totalmente Local)",
                    "active_provider": "ollama",
                    "recommended_model": "qwen2.5:14b ou qwen2.5:7b",
                    "optimal_parameters": {
                        "max_tokens": 2500,
                        "use_local_llm": True,
                        "deep_reasoning": True,
                        "enable_rewriting": True,
                        "query_expansion_variations": 3,
                        "use_brain": True
                    },
                    "strategy_name": "Balanced Performance & Zero API Cost",
                    "guidance_for_agent": (
                        "Hardware local rápido com VRAM intermediária (12GB a 16GB). "
                        "Recomenda-se orçamento de 2.500 tokens por consulta com expansão de 3 queries."
                    )
                }

            elif vram_tier == "ENTRY":
                return {
                    "runtime_environment": "LOCAL_GPU_ENTRY",
                    "hardware_detected": f"{hardware['device_name']} ({hardware['total_vram_gb']}GB VRAM)",
                    "financial_cost": "R$ 0,00 (Local)",
                    "active_provider": "ollama",
                    "recommended_model": "qwen2.5:7b ou llama3.1:8b",
                    "optimal_parameters": {
                        "max_tokens": 1500,
                        "use_local_llm": True,
                        "deep_reasoning": False,
                        "enable_rewriting": False,
                        "query_expansion_variations": 1,
                        "use_brain": True
                    },
                    "strategy_name": "Fast Local Inference",
                    "guidance_for_agent": (
                        "VRAM de entrada (6GB a 8GB). Mantenha consultas concisas (1.500 tokens) "
                        "para evitar swap de memória no host."
                    )
                }

            else: # CPU
                return {
                    "runtime_environment": "LOCAL_CPU",
                    "hardware_detected": "CPU Host (Sem GPU Dedicada)",
                    "financial_cost": "R$ 0,00",
                    "active_provider": "ollama",
                    "recommended_model": "all-MiniLM-L6-v2 (Embeddings) / Gemini Nuvem para geração",
                    "optimal_parameters": {
                        "max_tokens": 1200,
                        "use_local_llm": False,
                        "only_context": True,
                        "deep_reasoning": False,
                        "use_brain": True
                    },
                    "strategy_name": "Context-Only Bypass (Low Latency)",
                    "guidance_for_agent": (
                        "Ambiente sem aceleração de GPU. Recomenda-se usar `only_context=True` (bypass) "
                        "para extrair apenas o texto dos livros em milissegundos sem sobrecarregar a CPU."
                    )
                }

        # ==========================================
        # 2. Provedor Cloud: Gemini API (Free vs Paid)
        # ==========================================
        elif provider == "gemini":
            is_valid_key = bool(gemini_key and gemini_key != "sua_chave_gemini_aqui")
            # Se for chave com cota livre padrão
            is_free_tier = os.environ.get("GEMINI_TIER", "free").lower() == "free"

            if is_free_tier:
                return {
                    "runtime_environment": "CLOUD_API_FREE_TIER",
                    "hardware_detected": "Google Cloud TPU v4/v5 (Nuvem)",
                    "financial_cost": "Gratuito com Rate-Limit (15 RPM / 1.500 RPD / 1M TPM)",
                    "active_provider": "gemini",
                    "recommended_model": settings.GEMINI_MODEL or "gemini-2.0-flash",
                    "optimal_parameters": {
                        "max_tokens": 1800,
                        "use_local_llm": False,
                        "deep_reasoning": False,
                        "use_brain": True,
                        "enable_rewriting": False
                    },
                    "strategy_name": "Rate-Limit Guard & Brain Cache First",
                    "guidance_for_agent": (
                        "Você está utilizando a cota gratuita do Google Gemini. "
                        "Sempre consulte a Memória do Cérebro (`consult_brain` ou `use_brain=True`) "
                        "antes de disparar novas consultas para não estourar o limite de 15 requisições por minuto (HTTP 429)."
                    )
                }
            else:
                return {
                    "runtime_environment": "CLOUD_API_PAY_PER_TOKEN",
                    "hardware_detected": "Google Cloud Enterprise TPU (Nuvem)",
                    "financial_cost": "Cobrado por Milhão de Tokens (I/O)",
                    "active_provider": "gemini",
                    "recommended_model": settings.GEMINI_MODEL or "gemini-2.0-flash",
                    "optimal_parameters": {
                        "max_tokens": 1000,
                        "use_local_llm": False,
                        "only_context": True,
                        "deep_reasoning": False,
                        "use_brain": True,
                        "enable_rewriting": False
                    },
                    "strategy_name": "Strict Token Budgeting (>98% Cost Reduction)",
                    "guidance_for_agent": (
                        "API paga por consumo de tokens. Utilize `only_context=True` ou orçamento estrito de 1.000 tokens "
                        "com o algoritmo Elbow Cutoff para eliminar o ruído e reduzir em mais de 98% a fatura de tokens."
                    )
                }

        # Provedor genérico
        return {
            "runtime_environment": "GENERIC_PROVIDER",
            "hardware_detected": hardware["device_name"],
            "financial_cost": "Variável",
            "active_provider": provider,
            "optimal_parameters": {
                "max_tokens": 2000,
                "use_brain": True
            },
            "strategy_name": "Standard Adaptive RAG",
            "guidance_for_agent": "Utilize parâmetros balanceados (2.000 tokens)."
        }


# Instância Singleton para reuso
hardware_advisor_service = HardwareBudgetAdvisorService()
