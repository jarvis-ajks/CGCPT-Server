var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('SSH connected\n');

  var steps = [
    'echo "=== Step 1: Fix model_artifacts FK - allow NULL task_id ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 << \'PYEOF\'\nfrom models import SessionLocal, ModelArtifact, init_db\ninit_db()\ndb = SessionLocal()\nimport joblib, os, json\nmodels_dir = "/opt/CGCPT/models"\nfor f in sorted(os.listdir(models_dir)):\n    if not f.endswith(".pkl"):\n        continue\n    path = os.path.join(models_dir, f)\n    model_id = f.replace(".pkl", "")\n    existing = db.query(ModelArtifact).filter_by(id=model_id).first()\n    if existing:\n        print(f"Already: {model_id}")\n        continue\n    try:\n        model = joblib.load(path)\n        metrics = {}\n        if hasattr(model, "n_features_in_"):\n            metrics["n_features"] = int(model.n_features_in_)\n        if hasattr(model, "tree_"):\n            metrics["n_nodes"] = int(model.tree_.node_count)\n            metrics["max_depth_actual"] = int(model.tree_.max_depth)\n        if hasattr(model, "classes_"):\n            metrics["n_classes"] = len(model.classes_)\n            metrics["classes"] = [str(c) for c in model.classes_]\n        mtype = "decision_tree" if f.startswith("dt_") else "gradient_boosting"\n        meta_path = path.replace(".pkl", "_meta.json")\n        if os.path.exists(meta_path):\n            with open(meta_path) as mf:\n                meta = json.load(mf)\n            metrics.update(meta)\n        artifact = ModelArtifact(\n            id=model_id,\n            algorithm_id="stacking_predict",\n            task_id=None,\n            name=model_id,\n            model_type=mtype,\n            metrics=metrics,\n            file_path=path,\n            is_active=True,\n        )\n        db.add(artifact)\n        db.commit()\n        print(f"Registered: {model_id} type={mtype}")\n    except Exception as e:\n        db.rollback()\n        print(f"Failed: {model_id}: {e}")\ntotal = db.query(ModelArtifact).count()\nprint(f"Total artifacts: {total}")\ndb.close()\nPYEOF',

    'echo "=== Step 2: Fix material migration - scan ALL directories ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 << \'PYEOF\'\nimport os\nfrom models import SessionLocal, Material, init_db\nfrom datetime import datetime\ninit_db()\ndb = SessionLocal()\nexisting = set(m.id for m in db.query(Material.id).all())\nprint(f"Existing: {len(existing)}")\n\ndb_dir = "/opt/CGCPT/database"\nimported = 0\nskipped = 0\nfor root, dirs, files in os.walk(db_dir):\n    for fname in sorted(files):\n        if not fname.endswith(".cif"):\n            continue\n        mat_id = fname.replace(".cif", "")\n        if mat_id in existing:\n            skipped += 1\n            continue\n        rel_path = os.path.relpath(os.path.join(root, fname), db_dir)\n        parts = rel_path.split(os.sep)\n        topo_id = parts[0] if len(parts) > 0 else "unknown"\n        is_verified = "Verified" in rel_path or "verified" in rel_path\n        source = "verified" if is_verified else "raw"\n        mat = Material(\n            id=mat_id,\n            formula=mat_id,\n            space_group="P1",\n            topology_id=topo_id,\n            elements=[],\n            is_verified=is_verified,\n            source=source,\n            cif_path=rel_path,\n            created_at=datetime.utcnow(),\n            updated_at=datetime.utcnow(),\n        )\n        db.add(mat)\n        existing.add(mat_id)\n        imported += 1\n        if imported % 500 == 0:\n            try:\n                db.commit()\n                print(f"  Committed {imported}...")\n            except Exception as e:\n                db.rollback()\n                print(f"  Error: {e}")\ntry:\n    db.commit()\n    print(f"Done: imported={imported}, skipped={skipped}")\nexcept Exception as e:\n    db.rollback()\n    print(f"Final error: {e}")\nfinal_count = db.query(Material).count()\nprint(f"Total materials in DB: {final_count}")\ndb.close()\nPYEOF',

    'echo "=== Step 3: Verify counts ==="',
    'curl -s http://127.0.0.1:5001/api/db/stats 2>&1',

    'echo ""',
    'echo "=== Step 4: Check models API ==="',
    'curl -s http://127.0.0.1:5001/api/models 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); ms=d.get(\'models\',[]); print(f\'Models: {len(ms)}\'); [print(f\'  {m[\"id\"]}: {m[\"model_type\"]} active={m[\"is_active\"]} metrics_keys={list(m.get(\"metrics\",{}).keys())[:5]}\') for m in ms[:5]]" 2>&1',

    'echo "=== Step 5: Verify Celery tasks ==="',
    'curl -s http://127.0.0.1:5001/api/tasks 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); ts=d.get(\'tasks\',[]); [print(f\'  {t[\"task_id\"][:8]} {t[\"algorithm_id\"]} {t[\"status\"]} prog={t[\"progress\"]}\') for t in ts]" 2>&1',

    'echo "=== Step 6: Test real prediction ==="',
    'curl -s http://127.0.0.1:5001/api/stacking/models 2>&1 | head -c 300',
  ];

  var idx = 0;
  function runNext() {
    if (idx >= steps.length) { conn.end(); return; }
    conn.exec(steps[idx++], function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() { console.log(o.trim()); console.log('\n===SEP==='); runNext(); });
    });
  }
  runNext();
});
conn.connect(config);
