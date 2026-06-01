var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('SSH connected\n');

  var steps = [
    'echo "=== Step 1: Run DB migration ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import init_db, SessionLocal, migrate_from_filesystem; init_db(); db=SessionLocal(); r=migrate_from_filesystem(db); print(r); db.close()" 2>&1',

    'echo "=== Step 2: Verify migration ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import SessionLocal, Material, Prototype; db=SessionLocal(); print(f\'Materials: {db.query(Material).count()}\'); print(f\'Prototypes: {db.query(Prototype).count()}\'); db.close()" 2>&1',

    'echo "=== Step 3: Fix Celery worker PYTHONPATH ==="',
    'grep -n "PYTHONPATH" /etc/systemd/system/cgcpt-worker.service 2>/dev/null || echo "No PYTHONPATH set"',
    'grep -n "WorkingDirectory" /etc/systemd/system/cgcpt-worker.service 2>/dev/null || echo "No WorkingDirectory"',

    'echo "=== Step 4: Fix worker service ==="',
    'cat > /etc/systemd/system/cgcpt-worker.service << \'EOF\'\n[Unit]\nDescription=CGCPT Celery Worker\nAfter=network.target redis.service mysql.service\n\n[Service]\nType=forking\nUser=root\nWorkingDirectory=/opt/CGCPT\nEnvironment=PYTHONPATH=/opt/CGCPT\nExecStart=/opt/CGCPT/venv/bin/celery -A task_worker.celery_app worker --loglevel=info --concurrency=1 --pidfile=/var/run/cgcpt-worker.pid\nExecStop=/bin/kill -9 $(cat /var/run/cgcpt-worker.pid 2>/dev/null) 2>/dev/null || true\nRestart=always\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\nEOF\nsystemctl daemon-reload 2>&1 && echo "Worker service updated"',

    'echo "=== Step 5: Fix API service ==="',
    'cat /etc/systemd/system/cgcpt.service 2>/dev/null | head -20',

    'echo "=== Step 6: Restart services ==="',
    'systemctl restart cgcpt 2>&1',
    'systemctl restart cgcpt-worker 2>&1',
    'sleep 3',

    'echo "=== Step 7: Register existing models in DB ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "\nimport joblib, os, json\nfrom models import SessionLocal, ModelArtifact, init_db\ninit_db()\ndb = SessionLocal()\nmodels_dir = \'/opt/CGCPT/models\'\nfor f in os.listdir(models_dir):\n    if not f.endswith(\'.pkl\'): continue\n    path = os.path.join(models_dir, f)\n    model_id = f.replace(\'.pkl\', \'\')\n    existing = db.query(ModelArtifact).filter_by(id=model_id).first()\n    if existing: continue\n    try:\n        model = joblib.load(path)\n        metrics = {}\n        if hasattr(model, \'n_features_in_\'): metrics[\'n_features\'] = int(model.n_features_in_)\n        if hasattr(model, \'tree_\'): metrics[\'n_nodes\'] = int(model.tree_.node_count); metrics[\'max_depth_actual\'] = int(model.tree_.max_depth)\n        if hasattr(model, \'classes_\'): metrics[\'n_classes\'] = len(model.classes_); metrics[\'classes\'] = [str(c) for c in model.classes_]\n        mtype = \'decision_tree\' if f.startswith(\'dt_\') else \'gradient_boosting\'\n        meta_path = path.replace(\'.pkl\', \'_meta.json\')\n        if os.path.exists(meta_path):\n            with open(meta_path) as mf: meta = json.load(mf)\n            metrics.update(meta)\n        artifact = ModelArtifact(id=model_id, algorithm_id=\'stacking_predict\', task_id=\'\', name=model_id, model_type=mtype, metrics=metrics, file_path=path, is_active=True)\n        db.add(artifact)\n        print(f\'Registered: {model_id} ({mtype}) nodes={metrics.get(\"n_nodes\",\"?\")} classes={metrics.get(\"n_classes\",\"?\")}\')\n    except Exception as e:\n        print(f\'Failed: {model_id}: {e}\')\ndb.commit()\nprint(f\'Total artifacts: {db.query(ModelArtifact).count()}\')\ndb.close()\n" 2>&1',

    'echo "=== Step 8: Verify DB stats ==="',
    'curl -s http://127.0.0.1:5001/api/db/stats 2>&1',

    'echo ""',
    'echo "=== Step 9: Test Celery task ==="',
    'curl -s -X POST http://127.0.0.1:5001/api/tasks -H "Content-Type: application/json" -d \'{"algorithm_id":"stacking_train","input_data":{"test_ratio":0.2,"n_iterations":1}}\' 2>&1',

    'echo ""',
    'echo "=== Step 10: Wait and check task ==="',
    'sleep 8',
    'curl -s http://127.0.0.1:5001/api/tasks 2>&1 | head -c 800',

    'echo ""',
    'echo "=== Step 11: Verify models API ==="',
    'curl -s http://127.0.0.1:5001/api/models 2>&1 | head -c 500',

    'echo ""',
    'echo "=== Step 12: Final health check ==="',
    'curl -s http://127.0.0.1:5001/api/health 2>&1',
  ];

  var idx = 0;
  function runNext() {
    if (idx >= steps.length) { conn.end(); return; }
    conn.exec(steps[idx++], function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() { console.log(o.trim()); console.log('\n===SEPARATOR==='); runNext(); });
    });
  }
  runNext();
});
conn.connect(config);
