"""Session counts, Again share and true recall for recovery-test datasets.

    python experiments/recall_mode_stats.py data/recovery_test_overdue data/recovery_test_move

Compares recall_mode "line" and "move" on otherwise identical configs.
"""
import sys

import pandas as pd

print("| dataset | sessions per agent | Again share | mean true R at review | pass rate |")
print("|---|---|---|---|---|")
for d in sys.argv[1:]:
    rv = pd.read_csv(f"{d}/reviews.csv")
    t = pd.read_csv(f"{d}/hidden/truth.csv").set_index("review_id")
    v = rv[rv.review_status != "new"]
    print(f"| {d} | {len(v) / rv.agent_name.nunique():.0f} | {(v.grade == 1).mean():.1%} | "
          f"{t.loc[v.review_id, 'R_true'].mean():.3f} | {(v.grade > 1).mean():.3f} |")
