"""V2 + Tournament 결과 분석"""
import json
import statistics

# ==== V2 분석 ====
v2 = []
with open('C:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/data/v2.jsonl') as f:
    for line in f:
        v2.append(json.loads(line))

print(f'[V2] 총 레코드: {len(v2)}')

# session reset 찾기 (tick이 감소하는 지점)
resets = [0]
for i in range(1, len(v2)):
    if v2[i]['tick'] < v2[i-1]['tick']:
        resets.append(i)
resets.append(len(v2))
print(f'[V2] 세션 수: {len(resets)-1}')

# 마지막 세션
last_session = v2[resets[-2]:]
print(f'[V2] 마지막 세션 레코드: {len(last_session)}, tick {last_session[0]["tick"]} -> {last_session[-1]["tick"]}')
last = v2[-1]
print(f'[V2] 최종 상태: tick={last["tick"]} acc={last["acc"]:.3f} entropy={last["entropy"]:.3f} ret={last["ret"]*100:+.2f}% capital={last["capital"]:.0f} trades={last["trades"]}')

accs = [r['acc'] for r in last_session]
rets = [r['ret'] for r in last_session]
trades = [r['trades'] for r in last_session]

print(f'[V2] acc: avg {sum(accs)/len(accs):.3f} min {min(accs):.3f} max {max(accs):.3f} stdev {statistics.stdev(accs):.3f}')
print(f'[V2] ret: first {rets[0]*100:+.2f}% last {rets[-1]*100:+.2f}% max {max(rets)*100:+.2f}% min {min(rets)*100:+.2f}%')
print(f'[V2] trades: {trades[-1] - trades[0]}회 ({len(last_session)} ticks)')

print()
print('[V2] 구간별 추이:')
step = max(1, len(last_session)//15)
for i in range(0, len(last_session), step):
    r = last_session[i]
    print(f'  tick {r["tick"]:5d} | acc {r["acc"]:.3f} | ent {r["entropy"]:.3f} | ret {r["ret"]*100:+7.2f}% | trades {r["trades"]:5d}')

# ==== Tournament 분석 ====
print()
print('='*70)
eff = []
with open('C:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/data/effectiveness.jsonl') as f:
    for line in f:
        eff.append(json.loads(line))

print(f'[Tournament] 총 레코드: {len(eff)}')
last_t = eff[-1]
print(f'[Tournament] 최종: best {last_t["best"]:+.2f} | top10_avg {last_t["top10_avg"]:+.3f} | avg {last_t["avg"]:+.3f} | worst {last_t["worst"]:+.2f} | +ve {last_t["positive_pct"]}% | trades {last_t["trades"]}')

bests = [r['best'] for r in eff]
top10s = [r['top10_avg'] for r in eff]
avgs = [r['avg'] for r in eff]
worsts = [r['worst'] for r in eff]
poss = [r['positive_pct'] for r in eff]

print(f'[Tournament] best: min {min(bests):+.2f} max {max(bests):+.2f} avg {sum(bests)/len(bests):+.2f}')
print(f'[Tournament] top10_avg: avg {sum(top10s)/len(top10s):+.3f} max {max(top10s):+.3f}')
print(f'[Tournament] 전체 평균(5000개): avg {sum(avgs)/len(avgs):+.3f} min {min(avgs):+.3f}')
print(f'[Tournament] worst: min {min(worsts):+.2f} (최악 variant)')
print(f'[Tournament] positive_pct: avg {sum(poss)/len(poss):.1f}% max {max(poss):.1f}% min {min(poss):.1f}%')

print()
print('[Tournament] 시간 경과 추이:')
step = max(1, len(eff)//20)
for i in range(0, len(eff), step):
    r = eff[i]
    print(f'  t {r["t"]} | best {r["best"]:+6.2f} | top10 {r["top10_avg"]:+.3f} | avg {r["avg"]:+.3f} | +ve {r["positive_pct"]:4.1f}% | trades {r["trades"]:6d}')
