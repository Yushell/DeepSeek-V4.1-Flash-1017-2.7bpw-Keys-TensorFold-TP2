#!/usr/bin/env bash
# Run the recipe's acceptance gates against a live lane.
#   BASE=http://127.0.0.1:8888 MODEL=DeepSeek-V4.1-Flash-TF TOOLS=/path/to/recipe/tools ./scripts/verify.sh
# The gates and bench tools come from bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10 (Apache-2.0).
set -uo pipefail

BASE=${BASE:-http://127.0.0.1:8888}
MODEL=${MODEL:-DeepSeek-V4.1-Flash-TF}
TOOLS=${TOOLS:-./tools}
OUT=${OUT:-./verify-out}
mkdir -p "$OUT"

run() { echo "== $*"; "$@"; echo "-- rc=$?"; }

run python3 "$TOOLS/gates.py"   --base "$BASE" --model "$MODEL" --out "$OUT/gates.json"
run python3 "$TOOLS/needle.py"  --base "$BASE" --model "$MODEL" --lengths 131072 --depths 0.5 --out "$OUT/needle-131k.json"
run python3 "$TOOLS/kit_bench.py" --base "$BASE" --model "$MODEL" decode --set b --tokens 384 --reps 3 --out "$OUT/decode.json"
run python3 "$TOOLS/kit_bench.py" --base "$BASE" --model "$MODEL" sustained --streams 16 --tokens 256 --set b --seconds 90 --out "$OUT/sustained-16.json"

echo "== the long gate (about 9 minutes):"
echo "   python3 $TOOLS/needle.py --base $BASE --model $MODEL --lengths 1040000 --depths 0.5 --out $OUT/needle-1m.json"
