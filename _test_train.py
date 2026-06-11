import sys

sys.path.insert(0, ".")
from stacking_analyzer import scan_database_cifs, train_decision_tree

print("=== Extracting features ===")
samples = scan_database_cifs()
print(f"Total samples: {len(samples)}")

if samples:
    topo_dist = {}
    for s in samples:
        t = s["topology"]
        topo_dist[t] = topo_dist.get(t, 0) + 1
    print(f"Class distribution: {topo_dist}")

    fk = list(samples[0]["features"].keys())
    print(f"Feature count: {len(fk)}")

    print()
    print("=== Training Decision Tree ===")
    result = train_decision_tree(samples, test_ratio=0.2, n_iterations=3, cv_folds=3)

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
