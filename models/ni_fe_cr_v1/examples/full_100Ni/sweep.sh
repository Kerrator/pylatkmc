#!/usr/bin/env bash
# Full 80-config sweep: 10 vacancies × 8 temperatures.
# 500,000 steps × 4 MPI replicas per run.

set -e
cd "$(dirname "$0")"
SWEEP_DIR="$PWD"
REPO_ROOT="$(cd "$SWEEP_DIR/../../../.." && pwd)"
source "$REPO_ROOT/../pykmc_env/bin/activate"
SPEC="$REPO_ROOT/models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml"
SPEC_BAK="$SPEC.sweep.bak"
cp "$SPEC" "$SPEC_BAK"
trap 'cp "$SPEC_BAK" "$SPEC" && rm -f "$SPEC_BAK"' EXIT

TEMPS=(300 400 500 600 700 800 900 1200)
NVS=(1 2 3 4 5 6 7 8 9 10)
N_RANKS=4
MAX_STEPS=500000

for T in "${TEMPS[@]}"; do
  echo "=== T=${T} K ==="
  sed -i '' "s/^temperature_K.*/temperature_K   = ${T}.0/" "$SPEC"
  echo "  building proclist.c at T=${T}..."
  ( cd "$REPO_ROOT" && pylatkmc-gen build "$SPEC" >/dev/null )
  ( cd "$REPO_ROOT" && cmake --build build -j 4 2>&1 | tail -1 )

  for N in "${NVS[@]}"; do
    OUT="output_T${T}_${N}vac"
    INI="input_T${T}_${N}vac.ini"
    cat > "$INI" <<EOF
[run]
max_steps      = ${MAX_STEPS}
max_time_s     = 0
sample_every   = $((MAX_STEPS - 1))
summary_every  = 0
base_seed      = 42

[paths]
ratetable_path  = unused.kmcrt
initconfig_path = configs/${N}vac_T${T}.kmcinit
output_root     = ./${OUT}

[physics]
temperature_K = ${T}.0

[validation]
rng_replay_path =
EOF
    rm -rf "$OUT"
    START=$(python3 -c "import time; print(time.time())")
    /Users/stephenkerr/openmpi/bin/mpirun --oversubscribe -n ${N_RANKS} \
        "$REPO_ROOT/build/pylatkmc_ni_fe_cr_v1" "$INI" >/dev/null
    END=$(python3 -c "import time; print(time.time())")
    WALL=$(python3 -c "print(f'{${END} - ${START}:.3f}')")
    if [ -f "$OUT/aggregate_summary.json" ]; then
      python3 -c "
import json
p = '$OUT/aggregate_summary.json'
j = json.load(open(p))
j['wall_seconds'] = ${WALL}
json.dump(j, open(p, 'w'), indent=2)
"
      MSD=$(python3 -c "import json; print(f\"{json.load(open('$OUT/aggregate_summary.json'))['mean_msd_A2_mean']:.2e}\")")
      printf "  T=%-4d nvac=%2d  wall=%6.2fs  MSD=%s\n" $T $N $WALL "$MSD"
    else
      printf "  T=%-4d nvac=%2d  RUN FAILED\n" $T $N
    fi
  done
done
echo "done."
