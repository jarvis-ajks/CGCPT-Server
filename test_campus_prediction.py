import paramiko
import os
import json
import time

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"
REMOTE = "/archive/jarvisajks/cgcpt-web"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)


def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return (
        stdout.read().decode("utf-8", errors="replace").strip(),
        stderr.read().decode("utf-8", errors="replace").strip(),
    )


# Save model meta
print("保存模型元数据...")
meta = {
    "model_id": "gb_97393",
    "model_type": "gb",
    "test_accuracy": 0.9553,
    "train_accuracy": 1.0,
    "cv_mean": 0.9199,
    "cv_std": 0.0187,
    "n_samples": 2460,
    "n_classes": 3,
    "n_train": 1968,
    "n_test": 492,
    "model_name": "梯度提升(n=100,lr=0.2)",
    "seed": 42,
    "created": time.strftime("%Y-%m-%d %H:%M:%S"),
}
meta_json = json.dumps(meta, ensure_ascii=False)
run(f"echo '{meta_json}' > {REMOTE}/backend/models/gb_97393_meta.json")

# Test prediction with each test CIF
print("\n测试预测API...")
test_files_out, _ = run(f"ls {REMOTE}/backend/test_cifs/*.cif 2>/dev/null")
test_files = [f.strip() for f in test_files_out.split("\n") if f.strip() and f.endswith(".cif")]

for tf_path in test_files:
    fname = os.path.basename(tf_path)
    expected = "unknown"
    if "XO3_M7_XO3_M7_XO3_XO3" in fname:
        expected = "XO3-M7-XO3-M7-XO3-XO3"
    elif "XO2_T" in fname:
        expected = "XO3-M7-XO3-T-XO2-T-XO3"
    elif "XO_T" in fname:
        expected = "XO3-M7-XO3-T-XO-T-XO3-M7-XO3-T-XO-T-XO3-M7-XO3"

    # Use curl to test the API
    out, err = run(
        f"""curl -s -X POST http://127.0.0.1:5001/api/stacking/predict \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "import json; f=open('{tf_path}'); d=f.read(); f.close(); print(json.dumps({{'model_id':'gb_97393','cif_text':d}}))")" 2>&1""",
        timeout=60,
    )

    try:
        result = json.loads(out)
        pred = result.get("predicted_topology", "?")
        conf = result.get("confidence", 0)
        match = "✅" if pred == expected else "❌"
        print(
            f"  {match} {fname[:50]}: predicted={pred}, confidence={conf:.2%}, expected={expected}"
        )
    except:
        print(f"  ❓ {fname[:50]}: {out[:150]}")

# Verify models API
print("\n验证模型列表...")
out, _ = run("curl -s http://127.0.0.1:5001/api/stacking/models")
try:
    data = json.loads(out)
    models = data.get("models", [])
    print(f"  模型: {len(models)} 个")
    for m in models:
        print(
            f"    {m['model_id']}: acc={m.get('test_accuracy',0)}, type={m.get('model_type','?')}, samples={m.get('n_samples',0)}"
        )
except:
    print(f"  {out[:200]}")

ssh.close()
print("\n测试完成!")
