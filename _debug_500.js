var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  var cmds = [
    'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/ 2>&1',
    'curl -s http://127.0.0.1:5001/ 2>&1 | head -5',
    'curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" http://127.0.0.1/CGCPT/ 2>&1 | head -10',
    'curl -s -H "User-Agent: Mozilla/5.0 (iPhone)" http://127.0.0.1/CGCPT/ 2>&1 | head -10',
    'tail -20 /var/log/nginx/error.log 2>/dev/null',
    'journalctl -u cgcpt --no-pager -n 20 2>&1',
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
