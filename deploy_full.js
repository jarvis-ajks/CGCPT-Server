var Client = require('ssh2').Client;
var fs = require('fs');
var path = require('path');

var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };
var localBase = path.join(__dirname);
var remoteBase = '/opt/CGCPT';

var pythonFiles = [
  'api_server.py',
  'models.py',
  'task_worker.py',
  'task_engine.py',
  'cgcpt_plugin.py',
  'plugin_tool.py',
  'data_tools.py',
  'test_system.py',
  'deploy_server.py',
  'stacking_analyzer.py',
  'gunicorn.conf.py',
];

var pluginFiles = [
  'plugins/__init__.py',
  'plugins/cif_analyzer.py',
  'plugins/topology_stats.py',
];

var frontendFiles = [];
var distDir = path.join(localBase, 'web', 'dist');
function scanDir(dir, base) {
  var items = fs.readdirSync(dir);
  for (var i = 0; i < items.length; i++) {
    var full = path.join(dir, items[i]);
    var rel = base ? base + '/' + items[i] : items[i];
    if (fs.statSync(full).isDirectory()) {
      scanDir(full, rel);
    } else {
      frontendFiles.push(rel);
    }
  }
}
scanDir(distDir, '');

console.log('=== CGCPT Full Deploy ===');
console.log('Python files: ' + pythonFiles.length);
console.log('Plugin files: ' + pluginFiles.length);
console.log('Frontend files: ' + frontendFiles.length);
console.log('');

var conn = new Client();

conn.on('ready', function() {
  console.log('SSH connected\n');

  conn.sftp(function(e, sftp) {
    if (e) { console.error('SFTP error:', e); conn.end(); return; }

    var allFiles = [];
    for (var i = 0; i < pythonFiles.length; i++) {
      allFiles.push({ local: path.join(localBase, pythonFiles[i]), remote: remoteBase + '/' + pythonFiles[i] });
    }
    for (var i = 0; i < pluginFiles.length; i++) {
      allFiles.push({ local: path.join(localBase, pluginFiles[i]), remote: remoteBase + '/' + pluginFiles[i] });
    }
    for (var i = 0; i < frontendFiles.length; i++) {
      allFiles.push({ local: path.join(distDir, frontendFiles[i]), remote: remoteBase + '/web/dist/' + frontendFiles[i] });
    }

    var idx = 0, ok = 0, fail = 0;

    function ensureDir(remotePath, cb) {
      var dir = path.dirname(remotePath);
      sftp.mkdir(dir, function(err) {
        cb();
      });
    }

    function uploadOne() {
      if (idx >= allFiles.length) {
        console.log('\nUpload done: ' + ok + ' ok, ' + fail + ' failed');
        fixNginx();
        return;
      }
      var item = allFiles[idx++];
      if (!fs.existsSync(item.local)) {
        setTimeout(uploadOne, 10);
        return;
      }
      var content = fs.readFileSync(item.local);
      var shortName = item.remote.replace(remoteBase + '/', '');
      process.stdout.write('[' + idx + '/' + allFiles.length + '] ' + shortName + ' (' + content.length + 'B) ');

      ensureDir(item.remote, function() {
        sftp.writeFile(item.remote, content, function(err) {
          if (err) {
            fail++;
            console.log('FAIL: ' + err.message);
          } else {
            ok++;
            console.log('OK');
          }
          setTimeout(uploadOne, 30);
        });
      });
    }

    uploadOne();
  });

  function fixNginx() {
    console.log('\n=== Fixing Nginx for mobile access ===');

    var nginxCmds = [
      'cat /etc/nginx/nginx.conf',
      'ls /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null || true',
      'cat /etc/nginx/conf.d/*.conf 2>/dev/null || true',
      'cat /etc/nginx/sites-enabled/* 2>/dev/null || true',
    ];

    var cmdIdx = 0;
    var nginxInfo = '';

    function runNext() {
      if (cmdIdx >= nginxCmds.length) {
        analyzeNginx(nginxInfo);
        return;
      }
      conn.exec(nginxCmds[cmdIdx++], function(e, st) {
        var o = '';
        st.on('data', function(d) { o += d.toString(); });
        st.stderr.on('data', function(d) { o += d.toString(); });
        st.on('close', function() {
          nginxInfo += o + '\n---SEPARATOR---\n';
          runNext();
        });
      });
    }

    function analyzeNginx(info) {
      console.log('Analyzing current Nginx config...');

      var newConfig = [
        'server {',
        '    listen 80;',
        '    server_name 118.31.164.41;',
        '',
        '    # CGCPT frontend',
        '    location /CGCPT {',
        '        alias /opt/CGCPT/web/dist;',
        '        try_files $uri $uri/ /CGCPT/index.html;',
        '        add_header Cache-Control "no-cache, must-revalidate";',
        '    }',
        '',
        '    # CGCPT static assets - no cache issues',
        '    location /CGCPT/assets/ {',
        '        alias /opt/CGCPT/web/dist/assets/;',
        '        expires 30d;',
        '        add_header Cache-Control "public, immutable";',
        '    }',
        '',
        '    # CGCPT API proxy',
        '    location /CGCPT/api/ {',
        '        proxy_pass http://127.0.0.1:5000/api/;',
        '        proxy_set_header Host $host;',
        '        proxy_set_header X-Real-IP $remote_addr;',
        '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;',
        '        proxy_set_header X-Forwarded-Proto $scheme;',
        '        proxy_connect_timeout 300;',
        '        proxy_send_timeout 300;',
        '        proxy_read_timeout 300;',
        '        proxy_buffering off;',
        '    }',
        '',
        '    # CGCPT health check',
        '    location /CGCPT/health {',
        '        proxy_pass http://127.0.0.1:5000/health;',
        '        proxy_set_header Host $host;',
        '    }',
        '',
        '    # Default - AIClub or other apps',
        '    location / {',
        '        root /var/www/html;',
        '        index index.html;',
        '        try_files $uri $uri/ =404;',
        '    }',
        '}',
      ].join('\n');

      var writeCmd = "cat > /etc/nginx/conf.d/cgcpt.conf << 'NGINXEOF'\n" + newConfig + "\nNGINXEOF";

      conn.exec(writeCmd, function(e, st) {
        var o = '';
        st.on('data', function(d) { o += d.toString(); });
        st.stderr.on('data', function(d) { o += d.toString(); });
        st.on('close', function() {
          console.log('Nginx config written');

          conn.exec('nginx -t 2>&1', function(e, st) {
            var o = '';
            st.on('data', function(d) { o += d.toString(); });
            st.stderr.on('data', function(d) { o += d.toString(); });
            st.on('close', function() {
              console.log('Nginx test: ' + o.trim());

              if (o.indexOf('successful') >= 0 || o.indexOf('ok') >= 0) {
                conn.exec('nginx -s reload 2>&1', function(e, st) {
                  var o = '';
                  st.on('data', function(d) { o += d.toString(); });
                  st.on('close', function() {
                    console.log('Nginx reloaded: ' + o.trim());
                    restartServices();
                  });
                });
              } else {
                console.log('Nginx config test failed, skipping reload');
                restartServices();
              }
            });
          });
        });
      });
    }

    function restartServices() {
      console.log('\n=== Restarting CGCPT services ===');

      var cmds = [
        'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from models import init_db; init_db(); print(\'DB init OK\')" 2>&1',
        'cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "from task_worker import register_builtin_algorithms; register_builtin_algorithms(); print(\'Algorithms OK\')" 2>&1',
        'systemctl restart cgcpt-api 2>&1 || echo "cgcpt-api service not found"',
        'systemctl restart cgcpt-worker 2>&1 || echo "cgcpt-worker service not found"',
        'sleep 2 && systemctl is-active cgcpt-api cgcpt-worker 2>&1 || true',
      ];

      var cmdIdx = 0;
      function runNext() {
        if (cmdIdx >= cmds.length) {
          verify();
          return;
        }
        conn.exec(cmds[cmdIdx++], function(e, st) {
          var o = '';
          st.on('data', function(d) { o += d.toString(); });
          st.stderr.on('data', function(d) { o += d.toString(); });
          st.on('close', function() {
            console.log(o.trim());
            runNext();
          });
        });
      }
      runNext();
    }

    function verify() {
      console.log('\n=== Verification ===');

      var http = require('http');

      function checkURL(urlPath, label, callback) {
        var opts = { hostname: '118.31.164.41', port: 80, path: urlPath, timeout: 8000, headers: { 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) CGCPT-Verify' } };
        http.get(opts, function(res) {
          var d = [];
          res.on('data', function(c) { d.push(c); });
          res.on('end', function() {
            var body = Buffer.concat(d).toString('utf-8');
            console.log(label + ': HTTP ' + res.statusCode + ' (' + body.length + 'B)');
            if (body.indexOf('AIClub') >= 0) {
              console.log('  WARNING: Response contains AIClub redirect!');
            }
            callback();
          });
        }).on('error', function(err) {
          console.log(label + ': ERROR - ' + err.message);
          callback();
        });
      }

      checkURL('/CGCPT/', 'Mobile /CGCPT/', function() {
        checkURL('/CGCPT/api/health', 'API health', function() {
          checkURL('/CGCPT/api/db/stats', 'API stats', function() {
            checkURL('/CGCPT/api/algorithms', 'API algorithms', function() {
              console.log('\n=== Deploy Complete ===');
              conn.end();
            });
          });
        });
      });
    }

    runNext();
  }
});

conn.on('error', function(err) {
  console.error('SSH error:', err.message);
  process.exit(1);
});

conn.connect(config);
