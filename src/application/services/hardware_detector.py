import shutil
import subprocess
from typing import Any, Dict


def detect_gpu_hardware() -> Dict[str, Any]:
    """Detecta GPUs NVIDIA disponíveis via PyTorch/nvidia-smi ou faz fallback para CPU."""
    gpu_info = {
        "has_gpu": False,
        "device_name": "CPU",
        "total_vram_gb": 0.0,
        "free_vram_gb": 0.0,
        "vram_tier": "NONE",
    }
    try:
        import torch
        if torch.cuda.is_available():
            dev_name = torch.cuda.get_device_name(0)
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            free_mem = (torch.cuda.mem_get_info()[0] / (1024 ** 3)) if hasattr(torch.cuda, "mem_get_info") else total_mem * 0.8
            gpu_info.update({
                "has_gpu": True,
                "device_name": dev_name,
                "total_vram_gb": round(total_mem, 1),
                "free_vram_gb": round(free_mem, 1),
            })
    except Exception:
        pass

    if not gpu_info["has_gpu"] and shutil.which("nvidia-smi"):
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, encoding="utf-8").strip()
            if out:
                parts = out.split("\n")[0].split(",")
                gpu_info.update({
                    "has_gpu": True,
                    "device_name": parts[0].strip(),
                    "total_vram_gb": round(float(parts[1].strip()) / 1024, 1),
                    "free_vram_gb": round(float(parts[2].strip()) / 1024, 1),
                })
        except Exception:
            pass

    vram = gpu_info["total_vram_gb"]
    if vram >= 24.0:
        gpu_info["vram_tier"] = "ULTRA"
    elif vram >= 12.0:
        gpu_info["vram_tier"] = "MID"
    elif vram >= 6.0:
        gpu_info["vram_tier"] = "ENTRY"
    else:
        gpu_info["vram_tier"] = "CPU"
    return gpu_info
