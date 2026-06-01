var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  var cmds = [
    'echo "=== 1. Check stacking_analyzer ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from stacking_analyzer import scan_database_cifs; s=scan_database_cifs(); print(f\'Samples: {len(s)}\')" 2>&1',
    'echo "=== 2. Check models dir ==="',
    'ls -la /opt/CGCPT/models/ 2>/dev/null || echo "No models dir"',
    'echo "=== 3. Test training API ==="',
    'curl -s -X POST http://127.0.0.1:5001/api/stacking/train -H "Content-Type: application/json" -d \'{"test_ratio":0.2,"n_iterations":1}\' 2>&1 | head -c 500',
    'echo ""',
    'echo "=== 4. Check trained model files ==="',
    'ls -la /opt/CGCPT/models/*.pkl 2>/dev/null || echo "No pkl files"',
    'echo "=== 5. Test prediction API ==="',
    'curl -s -X POST http://127.0.0.1:5001/api/stacking/models 2>&1 | head -c 500',
    'echo ""',
    'echo "=== 6. Check DB stats ==="',
    'curl -s http://127.0.0.1:5001/api/db/stats 2>&1',
    'echo ""',
    'echo "=== 7. Check algorithms ==="',
    'curl -s http://127.0.0.1:5001/api/algorithms 2>&1 | head -c 500',
    'echo ""',
    'echo "=== 8. Check tasks ==="',
    'curl -s http://127.0.0.1:5001/api/tasks 2>&1 | head -c 500',
    'echo ""',
    'echo "=== 9. Check model artifacts in DB ==="',
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import SessionLocal, ModelArtifact; db=SessionLocal(); arts=db.query(ModelArtifact).all(); print(f\'Artifacts: {len(arts)}\'); [print(f\'  {a.id}: {a.name} active={a.is_active} type={a.model_type}\') for a in arts]; db.close()" 2>&1',
    'echo "=== 10. Check celery worker ==="',
    'systemctl status cgcpt-worker 2>&1 | head -10',
    'echo "=== 11. Redis check ==="',
    'redis-cli ping 2>&1',
  ];

  var idx = 0;
  function runNext() {
    if (idx >= cmds.length) { conn.end(); return; }
    conn.exec(cmds[idx++], function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() { console.log(o.trim()); console.log('---'); runNext(); });
    });
  }
  runNext();
});
conn.connect(config);
