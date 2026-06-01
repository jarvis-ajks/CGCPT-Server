var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('Fixing material migration with FK disabled...\n');

  var steps = [
    'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 << \'PYEOF\'\nimport os\nfrom models import SessionLocal, Material, init_db\nfrom datetime import datetime\nfrom sqlalchemy import text\ninit_db()\ndb = SessionLocal()\n\ntry:\n    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))\n    db.commit()\n    print("FK checks disabled")\nexcept Exception as e:\n    print(f"Warning: {e}")\n    db.rollback()\n\nexisting = set(m.id for m in db.query(Material.id).all())\nprint(f"Existing: {len(existing)}")\n\ndb_dir = "/opt/CGCPT/database"\nimported = 0\nskipped = 0\nfor root, dirs, files in os.walk(db_dir):\n    for fname in sorted(files):\n        if not fname.endswith(".cif"):\n            continue\n        mat_id = fname.replace(".cif", "")\n        if mat_id in existing:\n            skipped += 1\n            continue\n        rel_path = os.path.relpath(os.path.join(root, fname), db_dir)\n        parts = rel_path.split(os.sep)\n        dir_name = parts[0]\n        is_verified = "Verified" in rel_path\n        source = "verified" if is_verified else "raw"\n        topo_id = dir_name\n        mat = Material(\n            id=mat_id,\n            formula=mat_id,\n            space_group="P1",\n            topology_id=topo_id,\n            elements=[],\n            is_verified=is_verified,\n            source=source,\n            cif_path=rel_path,\n            created_at=datetime.utcnow(),\n            updated_at=datetime.utcnow(),\n        )\n        db.add(mat)\n        existing.add(mat_id)\n        imported += 1\n        if imported % 500 == 0:\n            try:\n                db.commit()\n                print(f"  Committed {imported}...")\n            except Exception as e:\n                db.rollback()\n                print(f"  Error at {imported}: {e}")\n\ntry:\n    db.commit()\n    print(f"Final commit: imported={imported}, skipped={skipped}")\nexcept Exception as e:\n    db.rollback()\n    print(f"Final error: {e}")\n\ntry:\n    db.execute(text("SET FOREIGN_KEY_CHECKS=1"))\n    db.commit()\n    print("FK checks re-enabled")\nexcept Exception:\n    pass\n\nfinal = db.query(Material).count()\nprint(f"Total materials in DB: {final}")\ndb.close()\nPYEOF',

    'echo "=== Verify ==="',
    'curl -s http://127.0.0.1:5001/api/db/stats 2>&1',

    'echo ""',
    'echo "=== Check models ==="',
    'curl -s http://127.0.0.1:5001/api/models 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); ms=d.get(\'models\',[]); print(f\'Models: {len(ms)}\'); [print(f\'  {m[\"id\"]}: {m[\"model_type\"]} active={m[\"is_active\"]}\') for m in ms[:5]]" 2>&1 || echo "parse error"',

    'echo "=== External verification ==="',
    'curl -s http://118.31.164.41/CGCPT/api/db/stats -H "User-Agent: Mozilla/5.0 (iPhone)" 2>&1',
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
