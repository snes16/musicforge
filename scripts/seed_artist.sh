#!/usr/bin/env bash
# seed_artist.sh — Prepare artist dataset for LoRA fine-tuning
#
# Usage:
#   ./scripts/seed_artist.sh --artist "Zemfira" --youtube-playlist <url> --output ./data/zemfira
#   ./scripts/seed_artist.sh --artist "Zemfira" --source-dir ~/music/zemfira --output ./data/zemfira

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ARTIST=""
SOURCE_DIR=""
YOUTUBE_PLAYLIST=""
OUTPUT_DIR=""
MAX_TRACKS=20
SAMPLE_RATE=44100
MAX_DURATION=180  # max seconds per track

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artist) ARTIST="$2"; shift 2 ;;
    --source-dir) SOURCE_DIR="$2"; shift 2 ;;
    --youtube-playlist) YOUTUBE_PLAYLIST="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --max-tracks) MAX_TRACKS="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 --artist <name> [--source-dir <path> | --youtube-playlist <url>] --output <path>"
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$ARTIST" || -z "$OUTPUT_DIR" ]]; then
  echo "Error: --artist and --output are required." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "============================================"
echo "  MusicForge — Seed Artist Dataset"
echo "============================================"
echo "  Artist:     $ARTIST"
echo "  Output:     $OUTPUT_DIR"
echo "  Max tracks: $MAX_TRACKS"
echo ""

# Option A: Download from YouTube playlist
if [[ -n "$YOUTUBE_PLAYLIST" ]]; then
  echo "Downloading from YouTube playlist..."
  if ! command -v yt-dlp &>/dev/null; then
    echo "Error: yt-dlp not installed. Run: pip install yt-dlp" >&2
    exit 1
  fi
  yt-dlp \
    --extract-audio \
    --audio-format wav \
    --audio-quality 0 \
    --max-downloads "$MAX_TRACKS" \
    --output "$OUTPUT_DIR/%(title)s.%(ext)s" \
    "$YOUTUBE_PLAYLIST"
fi

# Option B: Copy from local source directory
if [[ -n "$SOURCE_DIR" ]]; then
  if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: source directory '$SOURCE_DIR' not found." >&2
    exit 1
  fi
  echo "Copying from: $SOURCE_DIR"
  COUNT=0
  while IFS= read -r f && [[ $COUNT -lt $MAX_TRACKS ]]; do
    cp "$f" "$OUTPUT_DIR/"
    ((COUNT++))
    echo "  Copied: $(basename "$f")"
  done < <(find "$SOURCE_DIR" -name "*.mp3" -o -name "*.wav" -o -name "*.flac" | head -n "$MAX_TRACKS")
fi

# Normalize all tracks with ffmpeg
if command -v ffmpeg &>/dev/null; then
  echo ""
  echo "Normalizing audio (${SAMPLE_RATE}Hz, stereo, max ${MAX_DURATION}s)..."
  PROCESSED_DIR="$OUTPUT_DIR/normalized"
  mkdir -p "$PROCESSED_DIR"

  find "$OUTPUT_DIR" -maxdepth 1 \( -name "*.mp3" -o -name "*.wav" -o -name "*.flac" \) | while read -r f; do
    base=$(basename "$f" | sed 's/\.[^.]*$//')
    OUT="$PROCESSED_DIR/${base}.wav"
    ffmpeg -i "$f" \
      -ar "$SAMPLE_RATE" \
      -ac 2 \
      -t "$MAX_DURATION" \
      -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
      -y "$OUT" 2>/dev/null && echo "  Normalized: $base"
  done
  echo "  Normalized tracks saved to: $PROCESSED_DIR"
else
  echo "Warning: ffmpeg not found. Skipping normalization."
fi

# Write metadata file
cat > "$OUTPUT_DIR/artist_meta.json" <<METAEOF
{
  "artist": "$ARTIST",
  "output_dir": "$OUTPUT_DIR",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "track_count": $(find "$OUTPUT_DIR" -maxdepth 1 -name "*.mp3" -o -name "*.wav" -o -name "*.flac" | wc -l),
  "ready_for_training": true
}
METAEOF

echo ""
echo "============================================"
echo "  Dataset ready!"
echo "  Now run fine-tuning:"
echo "    ./scripts/train_lora.sh \\"
echo "      --artist \"$ARTIST\" \\"
echo "      --songs-dir $OUTPUT_DIR/normalized \\"
echo "      --output ${ARTIST,,}_lora_v1"
echo "============================================"
