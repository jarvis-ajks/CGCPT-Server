var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('SSH connected\n');

  var steps = [
    'echo "=== Step 1: Fix migration - skip duplicates ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 << \'PYEOF\'\nfrom models import SessionLocal, Material, Prototype, init_db\ninit_db()\ndb = SessionLocal()\nexisting_mats = set(m.id for m in db.query(Material.id).all())\nexisting_protos = set(p.id for p in db.query(Prototype.id).all())\nprint(f"Existing: {len(existing_mats)} materials, {len(existing_protos)} prototypes")\ndb.close()\n\nimport os, json, re\nfrom datetime import datetime\nfrom models import SessionLocal, Material, Prototype\n\ndb_dir = "/opt/CGCPT/database"\nif not os.path.exists(db_dir):\n    print("No database dir")\n    exit()\n\nproto_dirs = [d for d in os.listdir(db_dir) if os.path.isdir(os.path.join(db_dir, d))]\nprint(f"Found {len(proto_dirs)} directories")\n\nimported_mats = 0\nskipped_mats = 0\nfor dir_name in sorted(proto_dirs):\n    dir_path = os.path.join(db_dir, dir_name)\n    for sub in os.listdir(dir_path):\n        sub_path = os.path.join(dir_path, sub)\n        if not os.path.isdir(sub_path):\n            continue\n        for fname in sorted(os.listdir(sub_path)):\n            if not fname.endswith(".cif"):\n                continue\n            mat_id = fname.replace(".cif", "")\n            if mat_id in existing_mats:\n                skipped_mats += 1\n                continue\n            is_verified = sub.startswith("Verified")\n            source = "verified" if is_verified else "raw"\n            topo_id = dir_name\n            mat = Material(\n                id=mat_id,\n                formula=mat_id,\n                space_group="P1",\n                topology_id=topo_id,\n                elements=[],\n                is_verified=is_verified,\n                source=source,\n                cif_path=os.path.join(sub, fname),\n                created_at=datetime.utcnow(),\n                updated_at=datetime.utcnow(),\n            )\n            db.add(mat)\n            imported_mats += 1\n            if imported_mats % 200 == 0:\n                try:\n                    db.commit()\n                    print(f"  Committed {imported_mats} new materials...")\n                except Exception as e:\n                    db.rollback()\n                    print(f"  Commit error: {e}")\n\ntry:\n    db.commit()\n    print(f"Done: imported {imported_mats}, skipped {skipped_mats}")\nexcept Exception as e:\n    db.rollback()\n    print(f"Final commit error: {e}")\ndb.close()\nPYEOF',

    'echo "=== Step 2: Verify material count ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import SessionLocal, Material; db=SessionLocal(); print(f\'Materials: {db.query(Material).count()}\'); db.close()" 2>&1',

    'echo "=== Step 3: Fix Celery worker service ==="',
    'cat > /etc/systemd/system/cgcpt-worker.service << \'EOF\'\n[Unit]\nDescription=CGCPT Celery Worker\nAfter=network.target redis.service\n\n[Service]\nType=simple\nUser=root\nWorkingDirectory=/opt/CGCPT\nEnvironment=PYTHONPATH=/opt/CGCPT\nExecStart=/opt/CGCPT/venv/bin/celery -A task_worker.celery_app worker --loglevel=info --concurrency=1 --without-heartbeat\nRestart=always\nRestartSec=5\nTimeoutStartSec=120\n\n[Install]\nWantedBy=multi-user.target\nEOF\nsystemctl daemon-reload && echo "Worker service updated"',

    'echo "=== Step 4: Restart worker ==="',
    'pkill -f "celery.*task_worker" 2>/dev/null; sleep 1; systemctl start cgcpt-worker 2>&1; sleep 3; systemctl status cgcpt-worker 2>&1 | head -15',

    'echo "=== Step 5: Register models in DB ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 << \'PYEOF\'\nimport joblib, os, json\nfrom models import SessionLocal, ModelArtifact, init_db\ninit_db()\ndb = SessionLocal()\nmodels_dir = "/opt/CGCPT/models"\nif not os.path.exists(models_dir):\n    print("No models dir")\nelse:\n    for f in os.listdir(models_dir):\n        if not f.endswith(".pkl"):\n            continue\n        path = os.path.join(models_dir, f)\n        model_id = f.replace(".pkl", "")\n        existing = db.query(ModelArtifact).filter_by(id=model_id).first()\n        if existing:\n            print(f"Already registered: {model_id}")\n            continue\n        try:\n            model = joblib.load(path)\n            metrics = {}\n            if hasattr(model, "n_features_in_"):\n                metrics["n_features"] = int(model.n_features_in_)\n            if hasattr(model, "tree_"):\n                metrics["n_nodes"] = int(model.tree_.node_count)\n                metrics["max_depth_actual"] = int(model.tree_.max_depth)\n            if hasattr(model, "classes_"):\n                metrics["n_classes"] = len(model.classes_)\n                metrics["classes"] = [str(c) for c in model.classes_]\n            mtype = "decision_tree" if f.startswith("dt_") else "gradient_boosting"\n            meta_path = path.replace(".pkl", "_meta.json")\n            if os.path.exists(meta_path):\n                with open(meta_path) as mf:\n                    meta = json.load(mf)\n                metrics.update(meta)\n            artifact = ModelArtifact(\n                id=model_id,\n                algorithm_id="stacking_predict",\n                task_id="",\n                name=model_id,\n                model_type=mtype,\n                metrics=metrics,\n                file_path=path,\n                is_active=True,\n            )\n            db.add(artifact)\n            print(f"Registered: {model_id} type={mtype} nodes={metrics.get(chr(110)+chr(95)+chr(110)+chr(111)+chr(100)+chr(101)+chr(115), chr(63))}")\n        except Exception as e:\n            print(f"Failed: {model_id}: {e}")\n    db.commit()\n    total = db.query(ModelArtifact).count()\n    print(f"Total artifacts: {total}")\ndb.close()\nPYEOF',

    'echo "=== Step 6: Final DB stats ==="',
    'curl -s http://127.0.0.1:5001/api/db/stats 2>&1',

    'echo ""',
    'echo "=== Step 7: Check models API ==="',
    'curl -s http://127.0.0.1:5001/api/models 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\'Models: {len(d.get(chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(115),[]))}\')" 2>&1 || curl -s http://127.0.0.1:5001/api/models 2>&1 | head -c 300',

    'echo ""',
    'echo "=== Step 8: Test real training via API ==="',
    'curl -s -X POST http://127.0.0.1:5001/api/stacking/train -H "Content-Type: application/json" -d \'{"test_ratio":0.2,"n_iterations":1}\' 2>&1 | head -c 500',

    'echo ""',
    'echo "=== Step 9: Submit Celery training task ==="',
    'curl -s -X POST http://127.0.0.1:5001/api/tasks -H "Content-Type: application/json" -d \'{"algorithm_id":"stacking_train","input_data":{"test_ratio":0.2,"n_iterations":1}}\' 2>&1',

    'echo ""',
    'echo "=== Step 10: Wait and check ==="',
    'sleep 10',
    'curl -s http://127.0.0.1:5001/api/tasks 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); tasks=d.get(chr(116)+chr(97)+chr(115)+chr(107)+chr(115),[]); [print(f\'{t[chr(116)+chr(97)+chr(115)+chr(107)+chr(95)+chr(105)+chr(100)][:8]} {t[chr(97)+chr(108)+chr(103)+chr(111)+chr(114)+chr(105)+chr(116)+chr(104)+chr(109)+chr(95)+chr(105)+chr(100)]} {t[chr(115)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115)]} prog={t[chr(112)+chr(114)+chr(111)+chr(103)+chr(114)+chr(101)+chr(115)+chr(115)]}\') for t in tasks]" 2>&1 || curl -s http://127.0.0.1:5001/api/tasks 2>&1 | head -c 500',
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
