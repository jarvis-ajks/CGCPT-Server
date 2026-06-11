import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=180)
    return o.read().decode().strip(), e.read().decode().strip()


out, err = run(
    'curl -s -X POST http://127.0.0.1:5001/api/stacking/train -H "Content-Type: application/json" -d \'{"test_ratio": 0.2, "model_type": "auto", "n_iterations": 2, "cv_folds": 3}\''
)
data = json.loads(out)
print("Success:", data.get("success"))
if data.get("success"):
    bp = data.get("best_params", {})
    print(f'Best model: {bp.get("model_name")} (type: {bp.get("model_type")})')
    print(f'Test accuracy: {bp.get("test_accuracy")}')
    print(f'CV: {bp.get("cv_mean")} ± {bp.get("cv_std")}')
    print(f'Configs tested: {data.get("n_configs_tested")}')
    print(f'Iterations: {data.get("n_iterations")}')
    mc = data.get("model_comparison", {})
    print(f"\nModel comparison ({len(mc)} types):")
    for t, info in sorted(mc.items(), key=lambda x: x[1]["best_acc"], reverse=True):
        print(
            f'  {info["name"]}: best={info["best_acc"]:.4f} avg={info["avg_acc"]:.4f} ({info["count"]} tests)'
        )
    cm = data.get("confusion_matrix", {})
    if cm:
        print(f'\nConfusion matrix ({len(cm.get("labels",[]))} classes):')
        for row in cm.get("matrix", []):
            print("  ", row)
    fi = data.get("feature_importances", [])[:5]
    print(f"\nTop features: {fi}")
else:
    print("Error:", data.get("error"))

ssh.close()
