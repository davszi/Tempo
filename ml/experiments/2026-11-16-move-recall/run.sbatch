#!/bin/bash
# The whole experiment as one Slurm job on one A100 (PLAN.md). Submit from ml/:
#     sbatch experiments/2026-11-16-move-recall/run.sbatch
# The time limit is the agreed budget (3 A100-hours). A1 (py-fsrs) and data
# generation use the job's CPUs; the shared-trainer arms use the GPU.
#SBATCH --job-name=tempo-move-recall
#SBATCH --partition=batch
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=experiments/2026-11-16-move-recall/results/logs/slurm-%j.out
set -euo pipefail

E=experiments/2026-11-16-move-recall
R=$E/results
D=data/move-recall
PY=.venv/bin/python
export PYTHONHASHSEED=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export PYTHONPATH=$PWD  # train_pyfsrs.py runs as a script and must find tempo_ml (attempt 1 lacked this)
mkdir -p $R/logs

echo "host $(hostname)  job ${SLURM_JOB_ID:-none}  start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
$PY -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, torch.cuda.get_device_name(0))"
$PY -m pytest -q 2>&1 | tail -3

HOLDOUT=(20261112 20261122 20261132)
SEEDS=(20261111 20261121 20261131)
for i in 0 1 2; do
  s=${SEEDS[$i]}; h=${HOLDOUT[$i]}
  $PY -m tempo_ml.simulator.generate --out $D/seed-$s/train --config configs/fsrs-memory.json --seed $s > $R/logs/generate-$s-train.log
  $PY -m tempo_ml.simulator.generate --out $D/seed-$s/holdout --config configs/fsrs-memory-holdout.json --seed $h > $R/logs/generate-$s-holdout.log
  $PY -m tempo_ml.simulator.generate --out $D/seed-$s/reduced --config configs/fsrs-memory.json --seed $s --horizon-days 60 > $R/logs/generate-$s-reduced.log
done

# Reduced data must be a prefix of the full data, client by client.
$PY - <<'EOF'
import pandas as pd
for s in (20261111, 20261121, 20261131):
    full = pd.read_csv(f"data/move-recall/seed-{s}/train/sessions.csv")
    red = pd.read_csv(f"data/move-recall/seed-{s}/reduced/sessions.csv")
    for agent, g in red.groupby("agent_name", sort=False):
        f = full[full.agent_name == agent].head(len(g)).reset_index(drop=True)
        assert f.equals(g.reset_index(drop=True)), (s, agent)
    print(f"seed {s}: reduced data is a per-client prefix ({len(red)} of {len(full)} sessions)")
EOF

# A1 on the CPU, in the background.
for s in "${SEEDS[@]}"; do
  ( $PY $E/train_pyfsrs.py --data $D/seed-$s/train --out $R/seed-$s/A1 > $R/logs/seed-$s-A1.log 2>&1 ) &
done

# Shared-trainer arms on the GPU, one after another.
declare -A ARM=([A1c]=line [A1c-pass]=pass [A1c-acc]=accuracy [A1c-R]=true-recall)
for s in "${SEEDS[@]}"; do
  for name in A1c A1c-pass A1c-acc A1c-R; do
    $PY -m tempo_ml.fsrs.train --data $D/seed-$s/train --out $R/seed-$s/$name --arm ${ARM[$name]} \
      --device cuda --no-personalise > $R/logs/seed-$s-$name.log 2>&1
  done
  for name in A1c A1c-pass A1c-acc; do
    $PY -m tempo_ml.fsrs.train --data $D/seed-$s/reduced --out $R/seed-$s/reduced-$name --arm ${ARM[$name]} \
      --device cuda --no-personalise > $R/logs/seed-$s-reduced-$name.log 2>&1
  done
done
wait

$PY $E/compare.py --data $D --results $R --out $R > $R/logs/compare.log 2>&1
cat $R/tables.md
echo "end $(date -u +%FT%TZ)"
