import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stacking_analyzer
import numpy as np
from collections import Counter

print("=" * 70)
print("  训练问题诊断分析")
print("=" * 70)

samples = stacking_analyzer.scan_database_cifs()
print(f"\n总样本数: {len(samples)}")

topo_counts = Counter(s['topology'] for s in samples)
print(f"类别分布:")
for t, c in topo_counts.most_common():
    print(f"  {t}: {c}")

print("\n--- 问题1: 代理特征分析 ---")
print("检查每个特征是否直接编码了类别标签:")

feature_keys = sorted(samples[0]['features'].keys())
topos = sorted(topo_counts.keys())

for fk in feature_keys:
    vals_by_topo = {}
    for s in samples:
        t = s['topology']
        v = s['features'].get(fk)
        if v is not None:
            vals_by_topo.setdefault(t, []).append(float(v))

    unique_ranges = {}
    for t in topos:
        if t in vals_by_topo and vals_by_topo[t]:
            vals = vals_by_topo[t]
            unique_ranges[t] = (min(vals), max(vals))

    if len(unique_ranges) == len(topos):
        ranges = list(unique_ranges.values())
        no_overlap = all(
            ranges[i][1] < ranges[j][0] or ranges[j][1] < ranges[i][0]
            for i in range(len(ranges)) for j in range(i+1, len(ranges))
        )
        partial_overlap = True
        for i in range(len(ranges)):
            for j in range(i+1, len(ranges)):
                if ranges[i][1] < ranges[j][0] or ranges[j][1] < ranges[i][0]:
                    partial_overlap = False
                    break

        if no_overlap:
            print(f"  ❌ {fk}: 完全无重叠! 各类别范围:")
            for t in topos:
                if t in unique_ranges:
                    print(f"       {t[:40]:>40s}: [{unique_ranges[t][0]:.4f}, {unique_ranges[t][1]:.4f}]")
        elif partial_overlap:
            print(f"  ⚠️  {fk}: 部分重叠")
            for t in topos:
                if t in unique_ranges:
                    print(f"       {t[:40]:>40s}: [{unique_ranges[t][0]:.4f}, {unique_ranges[t][1]:.4f}]")
        else:
            print(f"  ✅ {fk}: 有重叠 (正常)")
    else:
        print(f"  ?  {fk}: 数据不完整")

print("\n--- 问题2: Raw/Verified数据重复 ---")
raw_files = set()
verified_files = set()
for s in samples:
    if s.get('source') == 'raw':
        raw_files.add(s['filename'])
    elif s.get('source') == 'verified':
        verified_files.add(s['filename'])

overlap = raw_files & verified_files
print(f"  Raw文件数: {len(raw_files)}")
print(f"  Verified文件数: {len(verified_files)}")
print(f"  重叠文件数: {len(overlap)}")
if overlap:
    print(f"  ⚠️  存在 {len(overlap)} 个重复文件!")
    print(f"  示例: {list(overlap)[:5]}")

print("\n--- 问题3: 特征与拓扑的直接映射 ---")
for fk in ['n_unique_elements', 'x_to_o_ratio', 'o_count', 'non_o_count']:
    print(f"\n  {fk}:")
    for t in topos:
        vals = [s['features'][fk] for s in samples if s['topology'] == t and s['features'].get(fk) is not None]
        if vals:
            unique_vals = sorted(set(float(v) for v in vals))
            print(f"    {t[:40]:>40s}: unique={unique_vals[:10]}{'...' if len(unique_vals)>10 else ''} (n_unique={len(unique_vals)})")
