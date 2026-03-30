#!/usr/bin/env bash
# download_models.sh — Download ACE-Step v1.5 model weights
#
# Usage:
#   ./scripts/download_models.sh [--dir ./checkpoints]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CHECKPOINT_DIR="$ROOT_DIR/checkpoints"
HF_REPO="ACE-Step/ACE-Steps-v1.5"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) CHECKPOINT_DIR="$2"; shift 2 ;;
    --repo) HF_REPO="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--dir <checkpoint-dir>] [--repo <hf-repo>]"
      exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

echo "============================================"
echo "  MusicForge — Download ACE-Step Models"
echo "============================================"
echo "  Repo:   $HF_REPO"
echo "  Output: $CHECKPOINT_DIR"
echo ""

mkdir -p "$CHECKPOINT_DIR"

# Method 1: huggingface-cli
if command -v huggingface-cli &>/dev/null; then
  echo "Using huggingface-cli..."
  huggingface-cli download "$HF_REPO" --local-dir "$CHECKPOINT_DIR"
  echo "Done."
  exit 0
fi

# Method 2: uv run ACE-Step downloader
if command -v uv &>/dev/null; then
  echo "Using uv run acestep-download..."
  cd "$ROOT_DIR"
  uv run acestep-download --checkpoint-dir "$CHECKPOINT_DIR"
  echo "Done."
  exit 0
fi

# Method 3: Python + huggingface_hub
if command -v python3 &>/dev/null; then
  echo "Using Python huggingface_hub..."
  python3 - <<PYEOF
try:
    from huggingface_hub import snapshot_download
    path = snapshot_download(
        repo_id="$HF_REPO",
        local_dir="$CHECKPOINT_DIR",
        ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
    )
    print(f"Downloaded to: {path}")
except ImportError:
    print("huggingface_hub not installed. Run: pip install huggingface_hub")
    raise SystemExit(1)
PYEOF
  exit 0
fi

echo "Error: No download method available." >&2
echo "Install one of: huggingface-cli, uv, or python3 + huggingface_hub" >&2
exit 1
