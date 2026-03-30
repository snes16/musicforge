import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from config import settings

router = APIRouter()


class LoRAModel(BaseModel):
    name: str
    description: Optional[str] = None
    file_size_mb: Optional[float] = None


class StylePreset(BaseModel):
    id: str
    label: str
    prompt_hint: str


class ModelsResponse(BaseModel):
    loras: List[LoRAModel]
    style_presets: List[StylePreset]
    base_model: str


STYLE_PRESETS = [
    StylePreset(id="indie_pop", label="Indie Pop", prompt_hint="indie pop, dreamy, lo-fi"),
    StylePreset(id="electronic", label="Electronic", prompt_hint="electronic, synth, pulsing beats"),
    StylePreset(id="hip_hop", label="Hip Hop", prompt_hint="hip hop, trap beats, 808s"),
    StylePreset(id="ambient", label="Ambient", prompt_hint="ambient, atmospheric, cinematic"),
    StylePreset(id="rock", label="Rock", prompt_hint="rock, electric guitar, drums"),
    StylePreset(id="jazz", label="Jazz", prompt_hint="jazz, piano, upright bass, brushed drums"),
    StylePreset(id="classical", label="Classical", prompt_hint="classical, orchestral, strings"),
    StylePreset(id="folk", label="Folk", prompt_hint="folk, acoustic guitar, warm vocals"),
    StylePreset(id="metal", label="Metal", prompt_hint="metal, heavy riffs, double bass drum"),
    StylePreset(id="rnb", label="R&B", prompt_hint="r&b, soulful vocals, smooth production"),
]


def _scan_loras() -> List[LoRAModel]:
    """Scan the LoRA directory for available adapters."""
    lora_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "acestep", "lora")
    loras = []
    if os.path.isdir(lora_dir):
        for fname in os.listdir(lora_dir):
            if fname.endswith((".pt", ".safetensors", ".bin")):
                fpath = os.path.join(lora_dir, fname)
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
                loras.append(LoRAModel(name=fname.split(".")[0], file_size_mb=size_mb))

    if not loras and settings.mock_gpu:
        loras = [
            LoRAModel(name="artist_lora_v1", description="Demo artist LoRA (mock)", file_size_mb=48.5),
            LoRAModel(name="zemfira_lora_v1", description="Zemfira style LoRA (mock)", file_size_mb=52.1),
        ]
    return loras


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available LoRA adapters and style presets."""
    return ModelsResponse(
        loras=_scan_loras(),
        style_presets=STYLE_PRESETS,
        base_model="acestep-v1.5",
    )


@router.get("/models/{model_id}/status")
async def get_model_status(model_id: str):
    """Get status of a specific model (loaded/unloaded)."""
    return {
        "model_id": model_id,
        "status": "loaded" if settings.mock_gpu else "unknown",
        "vram_mb": 3800 if settings.mock_gpu else None,
    }
