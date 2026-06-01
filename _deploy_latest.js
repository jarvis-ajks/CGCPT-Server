var Client = require('ssh2').Client;
var fs = require('fs');
var path = require('path');

var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };
var localBase = path.join(__dirname);
var remoteBase = '/opt/CGCPT';

var pythonFiles = ['api_server.py', 'models.py', 'task_worker.py', 'task_engine.py', 'cgcpt_plugin.py', 'plugin_tool.py', 'data_tools.py', 'test_system.py', 'stacking_analyzer.py'];
var pluginFiles = ['plugins/__init__.py', 'plugins/cif_analyzer.py', 'plugins/topology_stats.py'];

var frontendFiles = [];
var distDir = path.join(localBase, 'web', 'dist');
function scanDir(dir, base) {
  var items = fs.readdirSync(dir);
  for (var i = 0; i < items.length; i++) {
    var full = path.join(dir, items[i]);
    var rel = base ? base + '/' + items[i] : items[i];
    if (fs.statSync(full).isDirectory()) { scanDir(full, rel); }
    else { frontendFiles.push(rel); }
  }
}
scanDir(distDir, '');

console.log('=== CGCPT Deploy ===');
console.log('Python: ' + pythonFiles.length + ', Plugins: ' + pluginFiles.length + ', Frontend: ' + frontendFiles.length);

var conn = new Client();
conn.on('ready', function() {
  console.log('SSH connected\n');
  conn.sftp(function(e, sftp) {
    if (e) { console.error('SFTP error:', e); conn.end(); return; }

    var allFiles = [];
    for (var i = 0; i < pythonFiles.length; i++) allFiles.push({ local: path.join(localBase, pythonFiles[i]), remote: remoteBase + '/' + pythonFiles[i] });
    for (var i = 0; i < pluginFiles.length; i++) allFiles.push({ local: path.join(localBase, pluginFiles[i]), remote: remoteBase + '/' + pluginFiles[i] });
    for (var i = 0; i < frontendFiles.length; i++) allFiles.push({ local: path.join(distDir, frontendFiles[i]), remote: remoteBase + '/web/dist/' + frontendFiles[i] });

    var idx = 0, ok = 0, fail = 0;
    function uploadOne() {
      if (idx >= allFiles.length) {
        console.log('\nUpload: ' + ok + ' ok, ' + fail + ' failed');
        restartAndVerify();
        return;
      }
      var item = allFiles[idx++];
      if (!fs.existsSync(item.local)) { setTimeout(uploadOne, 10); return; }
      var content = fs.readFileSync(item.local);
      var shortName = item.remote.replace(remoteBase + '/', '');
      process.stdout.write('[' + idx + '/' + allFiles.length + '] ' + shortName + ' ');

      var dir = path.dirname(item.remote);
      sftp.mkdir(dir, function() {
        sftp.writeFile(item.remote, content, function(err) {
          if (err) { fail++; console.log('FAIL'); } else { ok++; console.log('OK'); }
          setTimeout(uploadOne, 20);
        });
      });
    }
    uploadOne();
  });

  function restartAndVerify() {
    console.log('\n=== Restarting services ===');
    var cmds = [
      'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import init_db; init_db(); print(\'DB OK\')" 2>&1',
      'systemctl restart cgcpt 2>&1',
      'systemctl restart cgcpt-worker 2>&1',
      'sleep 2 && curl -s http://127.0.0.1:5001/api/health 2>&1',
      'curl -s http://127.0.0.1:5001/api/auth/check 2>&1',
      'curl -s http://127.0.0.1:5001/api/models 2>&1 | head -c 200',
    ];

    var ci = 0;
    function runNext() {
      if (ci >= cmds.length) { verify(); return; }
      conn.exec(cmds[ci++], function(e, st) {
        var o = '';
        st.on('data', function(d) { o += d.toString(); });
        st.stderr.on('data', function(d) { o += d.toString(); });
        st.on('close', function() { console.log(o.trim()); console.log('---'); runNext(); });
      });
    }
    runNext();
  }

  function verify() {
    console.log('\n=== Verification ===');
    var http = require('http');
    function check(urlPath, label, ua, cb) {
      http.get({ hostname: '118.31.164.41', port: 80, path: urlPath, timeout: 8000, headers: { 'User-Agent': ua } }, function(res) {
        var d = [];
        res.on('data', function(c) { d.push(c); });
        res.on('end', function() {
          var body = Buffer.concat(d).toString('utf-8');
          var tags = [];
          if (body.indexOf('CGCPT') >= 0) tags.push('CGCPT');
          if (body.indexOf('success') >= 0) tags.push('API');
          if (body.indexOf('AIClub') >= 0) tags.push('AIClub!');
          console.log(label + ': HTTP ' + res.statusCode + ' ' + body.length + 'B ' + (tags.length ? '[' + tags.join(',') + ']' : ''));
          cb();
        });
      }).on('error', function(err) { console.log(label + ': ERROR ' + err.message); cb(); });
    }
    var mobile = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15';
    var desktop = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';

    check('/CGCPT/', 'Mobile /CGCPT/', mobile, function() {
      check('/CGCPT/api/health', 'API health', desktop, function() {
        check('/CGCPT/api/auth/check', 'API auth', desktop, function() {
          check('/CGCPT/api/models', 'API models', desktop, function() {
            console.log('\n=== Deploy Complete ===');
            conn.end();
          });
        });
      });
    });
  }
});
conn.connect(config);
