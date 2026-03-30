# LoRA Adapters

Place your trained LoRA adapter files in this directory.

## Supported Formats

- `.safetensors` (recommended)
- `.pt` (PyTorch checkpoint)
- `.bin` (binary checkpoint)

## Naming Convention

```
<artist_name>_lora_v<version>.<ext>
```

Examples:
- `zemfira_lora_v1.safetensors`
- `artist_lora_v1.pt`

## How to Add a LoRA

1. Train your LoRA using `scripts/train_lora.sh`
2. Copy the output `.safetensors` file to this directory
3. The backend will automatically detect it via `GET /api/models`
4. Select it in the frontend's Generate Form

## Training a New LoRA

```bash
./scripts/train_lora.sh \
  --artist "Artist Name" \
  --songs-dir ./data/my_artist \
  --output my_artist_lora_v1
```

Requirements:
- 5–20 audio tracks in MP3 or WAV format
- ~1 hour training time on RTX 5070 (8 tracks)
- ~16 GB VRAM recommended

## Pre-trained LoRAs

| Name | Description | Size |
|------|-------------|------|
| `artist_lora_v1` | Demo artist style | 48 MB |
| `zemfira_lora_v1` | Zemfira-inspired style | 52 MB |

> Note: Demo LoRAs are placeholders. Train your own for real results.
