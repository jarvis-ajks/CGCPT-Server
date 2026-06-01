var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  var cmds = [
    'ps aux | grep -E "gunicorn|flask|api_server|python3.*api" | grep -v grep',
    'ls /etc/systemd/system/cgcpt* 2>/dev/null || echo "No cgcpt systemd files"',
    'ls /opt/CGCPT/venv/bin/gunicorn 2>/dev/null || echo "No gunicorn"',
    'cat /opt/CGCPT/gunicorn.conf.py 2>/dev/null || echo "No gunicorn.conf.py"',
    'netstat -tlnp 2>/dev/null | grep -E "5000|8000" || ss -tlnp | grep -E "5000|8000"',
    'cat /etc/nginx/conf.d/cgcpt.conf 2>/dev/null || echo "No cgcpt nginx conf"',
    'ls /opt/CGCPT/web/dist/index.html 2>/dev/null && echo "Frontend exists" || echo "No frontend"',
  ];

  var idx = 0;
  function runNext() {
    if (idx >= cmds.length) { conn.end(); return; }
    conn.exec(cmds[idx++], function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() {
        console.log(o.trim());
        console.log('---');
        runNext();
      });
    });
  }
  runNext();
});
conn.connect(config);
