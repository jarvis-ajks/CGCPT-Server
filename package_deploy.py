#!/usr/bin/env python3
import os
import tarfile
import shutil

local_base = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.join(local_base, "_deploy_pkg")

if os.path.exists(pkg_dir):
    shutil.rmtree(pkg_dir)
os.makedirs(pkg_dir)

backend_files = [
    "api_server.py",
    "stacking_analyzer.py",
    "stack_main.py",
    "verify_topology.py",
    "gunicorn.conf.py",
    "setup_cloud.sh",
]

for f in backend_files:
    src = os.path.join(local_base, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(pkg_dir, f))
        print(f"  Added: {f}")
    else:
        print(f"  SKIP (not found): {f}")

db_dir = os.path.join(local_base, "database")
if os.path.exists(db_dir):
    dst = os.path.join(pkg_dir, "database")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(db_dir, dst)
    n_cifs = sum(1 for _, _, files in os.walk(db_dir) for f in files if f.endswith('.cif'))
    n_json = sum(1 for _, _, files in os.walk(db_dir) for f in files if f.endswith('.json'))
    print(f"  Added: database/ ({n_cifs} CIFs, {n_json} JSONs)")
else:
    print("  SKIP: database/ not found")

models_dir = os.path.join(local_base, "models")
if os.path.exists(models_dir):
    dst = os.path.join(pkg_dir, "models")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(models_dir, dst)
    n_models = len([f for f in os.listdir(models_dir) if f.endswith('.pkl')])
    print(f"  Added: models/ ({n_models} models)")
else:
    os.makedirs(os.path.join(pkg_dir, "models"), exist_ok=True)
    print("  Added: models/ (empty)")

web_dist = os.path.join(local_base, "web", "dist")
if os.path.exists(web_dist):
    dst = os.path.join(pkg_dir, "web", "dist")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(web_dist, dst)
    n_files = sum(len(files) for _, _, files in os.walk(web_dist))
    print(f"  Added: web/dist/ ({n_files} files)")
else:
    print("  SKIP: web/dist/ not found - build frontend first!")

test_dir = os.path.join(local_base, "test_cifs")
if os.path.exists(test_dir):
    dst = os.path.join(pkg_dir, "test_cifs")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(test_dir, dst)
    print(f"  Added: test_cifs/")

tar_path = os.path.join(local_base, "cgcpt_deploy.tar.gz")
with tarfile.open(tar_path, "w:gz", compresslevel=6) as tar:
    tar.add(pkg_dir, arcname="CGCPT")

size_mb = os.path.getsize(tar_path) / (1024 * 1024)
print(f"\nPackage created: {tar_path} ({size_mb:.1f} MB)")
print(f"\nTo deploy:")
print(f"  1. Upload to server:  scp cgcpt_deploy.tar.gz root@118.31.164.41:/tmp/")
print(f"  2. SSH into server:   ssh root@118.31.164.41")
print(f"  3. Extract:           mkdir -p /opt/CGCPT && cd /opt && tar xzf /tmp/cgcpt_deploy.tar.gz && mv CGCPT/* CGCPT/.* CGCPT 2>/dev/null; rm -rf /opt/CGCPT/CGCPT")
print(f"  4. Run setup:         cd /opt/CGCPT && bash setup_cloud.sh")

shutil.rmtree(pkg_dir)
