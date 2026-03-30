# LoRA Fine-tuning Guide

Train a custom LoRA adapter to generate music in the style of a specific artist.

---

## Prerequisites

- ACE-Step v1.5 installed and running
- 8+ audio tracks (mp3 or wav) from the target artist
- GPU with at least 16 GB VRAM (RTX 5070 or better recommended)
- ~1 hour training time for 8 tracks

---

## Quick Start

```bash
# Prepare dataset and train LoRA
./scripts/train_lora.sh \
  --artist "Земфира" \
  --songs-dir ./data/zemfira \
  --output lora_zemfira_v1
```

The trained adapter will be saved to `./acestep/lora/lora_zemfira_v1.safetensors`.

---

## Step-by-Step

### 1. Prepare audio files

Collect 8–20 tracks in mp3 or wav format. Minimum recommended:
- 8 tracks
- Each track at least 60 seconds
- Good audio quality (no heavy compression artifacts)

Place them in a directory:
```
data/
└── zemfira/
    ├── track01.mp3
    ├── track02.mp3
    └── ...
```

### 2. Preprocess dataset

The `seed_artist.sh` script prepares the dataset (transcription, segmentation):

```bash
./scripts/seed_artist.sh \
  --songs-dir ./data/zemfira \
  --output ./data/zemfira_processed
```

### 3. Train LoRA

```bash
./scripts/train_lora.sh \
  --artist "Artist Name" \
  --songs-dir ./data/artist_processed \
  --output lora_artist_v1 \
  [--epochs 10] \
  [--rank 32] \
  [--lr 1e-4]
```

Options:
| Flag | Default | Description |
|------|---------|-------------|
| `--artist` | required | Artist display name |
| `--songs-dir` | required | Path to audio files or preprocessed dataset |
| `--output` | required | Output LoRA name (saved to `./acestep/lora/`) |
| `--epochs` | `10` | Number of training epochs |
| `--rank` | `32` | LoRA rank (higher = more parameters, slower) |
| `--lr` | `1e-4` | Learning rate |

### 4. Verify

After training, the LoRA appears in the API:

```bash
curl http://localhost:8000/api/models
```

```json
{
  "loras": [
    {
      "name": "lora_zemfira_v1",
      "description": "Земфира style LoRA",
      "file_size_mb": 45
    }
  ]
}
```

### 5. Use in generation

Select the LoRA in the UI, or via API:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "indie rock, emotional female vocals, acoustic guitar",
    "duration": 60,
    "lora_name": "lora_zemfira_v1"
  }'
```

---

## Training Time Estimates

| GPU | Tracks | Epochs | Time |
|-----|--------|--------|------|
| RTX 5070 (16 GB) | 8 | 10 | ~1 hour |
| RTX 4090 (24 GB) | 8 | 10 | ~35 min |
| RTX 3090 (24 GB) | 8 | 10 | ~1.5 hours |

---

## Tips

- **More tracks = better results.** 20+ tracks produces noticeably better style transfer.
- **LoRA rank**: `32` is a good default. Use `64` for more expressive models (2x VRAM).
- **Overfitting**: If the model sounds too close to the originals, reduce epochs.
- **Multiple artists**: Train separate LoRAs and switch at generation time.

---

## Adding a LoRA manually

Copy a pre-trained `.safetensors` file to `./acestep/lora/`:

```bash
cp my_custom_lora.safetensors ./acestep/lora/
```

The backend auto-discovers files in this directory on startup (or call `GET /api/models` to refresh).

---

## See also

- [ACE-Step fine-tuning docs](http://localhost:8001/docs) — official ACE-Step API reference
- [GPU Farm Architecture](gpu_farm_arch.md)
- [REST API Reference](api.md)
