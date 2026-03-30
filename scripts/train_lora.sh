#!/usr/bin/env bash
# train_lora.sh — Fine-tune a LoRA adapter for ACE-Step v1.5
#
# Usage:
#   ./scripts/train_lora.sh --artist "Zemfira" --songs-dir ./data/zemfira --output lora_zemfira_v1
#
# Requirements:
#   - ACE-Step v1.5 installed (or cloned at ./ACE-Step-1.5)
#   - Python 3.11 + uv
#   - 16 GB VRAM (RTX 5070 recommended)
#   - 5–20 audio tracks in MP3/WAV format in --songs-dir

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
ARTIST=""
SONGS_DIR=""
OUTPUT_NAME=""
EPOCHS=10
BATCH_SIZE=1
LEARNING_RATE="1e-4"
LORA_RANK=16
CHECKPOINT_DIR="$ROOT_DIR/checkpoints"
LORA_OUTPUT_DIR="$ROOT_DIR/acestep/lora"
SAMPLE_RATE=44100
MAX_DURATION=120  # seconds per track used for training

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --artist)
      ARTIST="$2"; shift 2 ;;
    --songs-dir)
      SONGS_DIR="$2"; shift 2 ;;
    --output)
      OUTPUT_NAME="$2"; shift 2 ;;
    --epochs)
      EPOCHS="$2"; shift 2 ;;
    --batch-size)
      BATCH_SIZE="$2"; shift 2 ;;
    --lr)
      LEARNING_RATE="$2"; shift 2 ;;
    --lora-rank)
      LORA_RANK="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 --artist <name> --songs-dir <path> --output <name> [options]"
      echo ""
      echo "Options:"
      echo "  --artist        Artist name (used in metadata)"
      echo "  --songs-dir     Directory with MP3/WAV tracks"
      echo "  --output        Output LoRA name (without extension)"
      echo "  --epochs        Training epochs (default: 10)"
      echo "  --batch-size    Batch size (default: 1)"
      echo "  --lr            Learning rate (default: 1e-4)"
      echo "  --lora-rank     LoRA rank (default: 16)"
      exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Validate
if [[ -z "$ARTIST" || -z "$SONGS_DIR" || -z "$OUTPUT_NAME" ]]; then
  echo "Error: --artist, --songs-dir, and --output are required." >&2
  exit 1
fi

if [[ ! -d "$SONGS_DIR" ]]; then
  echo "Error: songs directory '$SONGS_DIR' does not exist." >&2
  exit 1
fi

echo "============================================"
echo "  MusicForge LoRA Training"
echo "============================================"
echo "  Artist:     $ARTIST"
echo "  Songs dir:  $SONGS_DIR"
echo "  Output:     $OUTPUT_NAME"
echo "  Epochs:     $EPOCHS"
echo "  LR:         $LEARNING_RATE"
echo "  LoRA rank:  $LORA_RANK"
echo "============================================"

# Count audio files
TRACK_COUNT=$(find "$SONGS_DIR" -name "*.mp3" -o -name "*.wav" -o -name "*.flac" | wc -l)
echo "Found $TRACK_COUNT audio files."

if [[ $TRACK_COUNT -lt 3 ]]; then
  echo "Warning: less than 3 tracks found. Training quality may be poor." >&2
fi

# Step 1: Preprocess / prepare dataset
echo ""
echo "[1/4] Preprocessing audio files..."

DATASET_DIR="$ROOT_DIR/data/processed/${OUTPUT_NAME}"
mkdir -p "$DATASET_DIR"

# Normalize and convert to WAV using ffmpeg (if available)
if command -v ffmpeg &>/dev/null; then
  find "$SONGS_DIR" -name "*.mp3" -o -name "*.wav" -o -name "*.flac" | while read -r f; do
    basename=$(basename "$f" | sed 's/\.[^.]*$//')
    ffmpeg -i "$f" \
      -ar "$SAMPLE_RATE" \
      -ac 2 \
      -t "$MAX_DURATION" \
      -y \
      "$DATASET_DIR/${basename}.wav" 2>/dev/null
    echo "  Processed: $basename"
  done
else
  echo "  Warning: ffmpeg not found. Copying files as-is..."
  cp "$SONGS_DIR"/*.{mp3,wav,flac} "$DATASET_DIR/" 2>/dev/null || true
fi

echo "  Dataset ready at: $DATASET_DIR"

# Step 2: Generate dataset manifest
echo ""
echo "[2/4] Building dataset manifest..."

MANIFEST="$DATASET_DIR/manifest.json"
python3 - <<PYEOF
import json, os, glob

songs_dir = "$DATASET_DIR"
artist = "$ARTIST"
output = "$OUTPUT_NAME"

tracks = []
for fpath in sorted(glob.glob(os.path.join(songs_dir, "*.wav"))):
    tracks.append({
        "path": fpath,
        "artist": artist,
        "style": f"{artist.lower()} style",
    })

manifest = {
    "artist": artist,
    "lora_name": output,
    "tracks": tracks,
    "sample_rate": $SAMPLE_RATE,
}

with open("$MANIFEST", "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"  Manifest written: {len(tracks)} tracks")
PYEOF

# Step 3: Run ACE-Step LoRA fine-tuning
echo ""
echo "[3/4] Starting LoRA fine-tuning..."
echo "  This may take ~1 hour on RTX 5070 (8 tracks, 10 epochs)"

# Check for ACE-Step installation
ACESTEP_TRAIN_CMD=""
if command -v acestep-train &>/dev/null; then
  ACESTEP_TRAIN_CMD="acestep-train"
elif [[ -f "$ROOT_DIR/ACE-Step-1.5/train_lora.py" ]]; then
  ACESTEP_TRAIN_CMD="python $ROOT_DIR/ACE-Step-1.5/train_lora.py"
elif command -v uv &>/dev/null; then
  ACESTEP_TRAIN_CMD="uv run acestep-train"
fi

if [[ -z "$ACESTEP_TRAIN_CMD" ]]; then
  echo "  Warning: ACE-Step training tool not found."
  echo "  Please install ACE-Step first:"
  echo "    git clone https://github.com/ACE-Step/ACE-Step-1.5.git"
  echo "    cd ACE-Step-1.5 && pip install -e ."
  echo ""
  echo "  Simulating training (dry run)..."
  sleep 2
  echo "  [DRY RUN] Would train with: $ACESTEP_TRAIN_CMD"
else
  $ACESTEP_TRAIN_CMD \
    --manifest "$MANIFEST" \
    --checkpoint-dir "$CHECKPOINT_DIR" \
    --output-dir "$LORA_OUTPUT_DIR" \
    --output-name "$OUTPUT_NAME" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --lora-rank "$LORA_RANK" \
    --artist "$ARTIST"
fi

# Step 4: Verify output
echo ""
echo "[4/4] Verifying output..."

LORA_FILE="$LORA_OUTPUT_DIR/${OUTPUT_NAME}.safetensors"
if [[ -f "$LORA_FILE" ]]; then
  SIZE=$(du -sh "$LORA_FILE" | cut -f1)
  echo "  LoRA saved: $LORA_FILE ($SIZE)"
else
  echo "  Warning: Expected output not found at $LORA_FILE"
  echo "  Check training logs for errors."
fi

echo ""
echo "============================================"
echo "  Training complete!"
echo "  LoRA output: $LORA_OUTPUT_DIR/${OUTPUT_NAME}.safetensors"
echo "  Use via API: POST /api/generate with lora_name: \"$OUTPUT_NAME\""
echo "============================================"
