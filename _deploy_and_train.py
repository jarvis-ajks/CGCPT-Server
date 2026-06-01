import paramiko
import os
import sys

HOST = "118.31.164.41"
USER = "root"
KEY = r"D:\Projects\CGCPT-Server\id_ed25519"

LOCAL_STACKING = r"D:\Projects\CGCPT-Server\stacking_analyzer.py"
REMOTE_STACKING = "/opt/CGCPT/stacking_analyzer.py"

LOCAL_API = r"D:\Projects\CGCPT-Server\api_server.py"
REMOTE_API = "/opt/CGCPT/api_server.py"

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, key_filename=KEY, timeout=30)
    return ssh

def upload_file(ssh, local, remote):
    sftp = ssh.open_sftp()
    sftp.put(local, remote)
    sftp.close()
    print(f"[OK] Uploaded {local} -> {remote}")

def run_cmd(ssh, cmd, timeout=600):
    print(f"\n>>> {cmd[:120]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    return out, err

def main():
    print("=== Connecting to server ===")
    ssh = connect()
    print("[OK] Connected")

    print("\n=== Part 1: Upload stacking_analyzer.py ===")
    upload_file(ssh, LOCAL_STACKING, REMOTE_STACKING)

    print("\n=== Part 2: Upload api_server.py ===")
    upload_file(ssh, LOCAL_API, REMOTE_API)

    print("\n=== Part 3: Restart service ===")
    run_cmd(ssh, "systemctl restart cgcpt")
    run_cmd(ssh, "sleep 3 && systemctl status cgcpt --no-pager -l")

    print("\n=== Part 4: Run training ===")
    train_py = """import sys
sys.path.insert(0, ".")
from stacking_analyzer import scan_database_cifs, train_decision_tree

print("=== Extracting features ===")
samples = scan_database_cifs()
print(f"Total samples: {len(samples)}")

topo_dist = {}
for s in samples:
    t = s["topology"]
    topo_dist[t] = topo_dist.get(t, 0) + 1
print(f"Class distribution: {topo_dist}")

fk = list(samples[0]["features"].keys())
print(f"Feature count: {len(fk)}")

print()
print("=== Training Decision Tree ===")
result = train_decision_tree(samples, test_ratio=0.2, n_iterations=5, cv_folds=5)

if result["success"]:
    bp = result["best_params"]
    print(f"Model ID: {result['model_id']}")
    print(f"Model: {bp['model_name']}")
    print(f"Test Accuracy: {bp['test_accuracy']*100:.1f}%")
    print(f"Train Accuracy: {bp['train_accuracy']*100:.1f}%")
    print(f"Overfit: {bp.get('overfit', 0)*100:.1f}%")
    print(f"CV Mean: {bp['cv_mean']*100:.1f}%")
    print(f"CV Std: {bp['cv_std']*100:.1f}%")
    print(f"Train: {bp['n_train']}, Test: {bp['n_test']}")
    print(f"Configs tested: {result['n_configs_tested']}")

    print()
    print("=== Top 10 Feature Importances ===")
    for fname, fimp in result["feature_importances"][:10]:
        print(f"  {fname}: {fimp:.4f}")

    print()
    print("=== Classification Report ===")
    for cls, metrics in result["classification_report"].items():
        if isinstance(metrics, dict):
            p = metrics.get("precision", 0)
            r = metrics.get("recall", 0)
            f1 = metrics.get("f1-score", 0)
            sup = metrics.get("support", 0)
            print(f"  {cls}: P={p:.2f} R={r:.2f} F1={f1:.2f} support={sup}")
else:
    print(f"Training failed: {result['error']}")
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(train_py)
        tmp_path = f.name
    upload_file(ssh, tmp_path, "/opt/CGCPT/_run_train.py")
    os.unlink(tmp_path)
    run_cmd(ssh, "cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 /opt/CGCPT/_run_train.py", timeout=600)

    print("\n=== Part 5: Verify API ===")
    run_cmd(ssh, "curl -s http://localhost/CGCPT/api/health | python3 -m json.tool")
    run_cmd(ssh, "curl -s http://localhost:5001/api/health | python3 -m json.tool")

    ssh.close()
    print("\n=== All done ===")

if __name__ == "__main__":
    main()
