import collections, glob, json, statistics

def load():
    for path in sorted(glob.glob("runs28/*.json")):
        yield json.load(open(path))

rewards, statuses = collections.Counter(), collections.Counter()
errors = collections.Counter()
error_examples = {}
agents = []
problem_hits = collections.defaultdict(lambda: [0, 0])   # solved, attempted (validator only)

for blob in load():
    row, evs = blob["row"], blob["evaluations"]
    per_stage, costs, durations = {}, [], []
    agent_errors = collections.Counter()
    for ev in evs:
        group = ev["evaluation_set_group"]
        solved = total = 0
        for run in ev["runs"]:
            statuses[run["status"]] += 1
            reward = run.get("verifier_reward")
            rewards[reward] += 1
            code = run.get("error_code")
            if code or run["status"] not in ("finished",):
                key = code or ("status:" + run["status"])
                errors[key] += 1
                agent_errors[key] += 1
                error_examples.setdefault(key, (run.get("error_message") or "")[:220])
            total += 1
            if reward == 1.0:
                solved += 1
            if run.get("cost_usd") is not None:
                costs.append(run["cost_usd"])
            if group == "validator":
                hit = problem_hits[run["problem_alias"]]
                hit[1] += 1
                if reward == 1.0:
                    hit[0] += 1
        per_stage.setdefault(group, []).append((solved, total))
    agents.append({
        "rank": row["rank"], "name": row.get("name"), "score": row.get("final_score"),
        "approved": row.get("approved"), "cost": row.get("average_cost_usd"),
        "runtime": row.get("average_runtime_seconds"), "stages": per_stage,
        "errors": agent_errors, "run_costs": costs,
    })

def rate(pairs):
    s = sum(p[0] for p in pairs); t = sum(p[1] for p in pairs)
    return "%2d/%-3d %5.1f%%" % (s, t, 100.0 * s / t if t else 0)

print("RANK NAME       SCORE APPR  SCREEN1      SCREEN2      VALIDATOR(3x)   $/run  s/run")
for a in sorted(agents, key=lambda x: x["rank"]):
    print("%4d %-10s %5.2f %-5s %s %s %s  %.4f %5.0f" % (
        a["rank"], (a["name"] or "?")[:10], a["score"], a["approved"],
        rate(a["stages"].get("screener_1", [])), rate(a["stages"].get("screener_2", [])),
        rate(a["stages"].get("validator", [])),
        a["cost"] or 0, a["runtime"] or 0))

print("\nRUN STATUS across all %d runs of the top 20:" % sum(statuses.values()))
for k, v in statuses.most_common():
    print("  %-28s %5d" % (k, v))
print("\nVERIFIER REWARD distribution:")
for k, v in sorted(rewards.items(), key=lambda kv: -kv[1]):
    print("  %-28s %5d" % (str(k), v))
print("\nERROR CODES / non-finished statuses:")
for k, v in errors.most_common():
    print("  %-28s %5d  %s" % (k, v, error_examples.get(k, "")[:110]))
