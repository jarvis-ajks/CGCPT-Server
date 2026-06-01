import os, shutil, random
from pathlib import Path
from collections import Counter

db = Path(r'd:\Projects\CGCPT-Server\database')
output = Path(r'd:\Projects\CGCPT-Server\test_cifs')
output.mkdir(exist_ok=True)

for old in output.glob('*.cif'):
    old.unlink()

topo_dirs = {}
for d in db.iterdir():
    if d.is_dir() and d.name.startswith('Raw_Proto_'):
        label = d.name.replace('Raw_Proto_', '')
        cifs = list(d.glob('*.cif'))
        if len(cifs) >= 2:
            topo_dirs[label] = cifs

print(f"找到 {len(topo_dirs)} 个拓扑类别:")
for label, cifs in topo_dirs.items():
    print(f"  {label}: {len(cifs)} CIFs")

print("\n随机抽取测试样本...")
for label, cifs in topo_dirs.items():
    n = min(3, len(cifs))
    selected = random.sample(cifs, n)
    for i, cif in enumerate(selected):
        fname = f"test_{label.replace('-', '_')}_{i+1}.cif"
        shutil.copy2(cif, output / fname)
        print(f"  {fname} <- {cif.name}")

print(f"\n测试CIF文件保存在: {output}")
print(f"共 {len(list(output.glob('*.cif')))} 个文件")
