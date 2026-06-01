var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('SSH connected\n');

  var cmds = [
    'echo "=== All nginx configs ==="',
    'cat /etc/nginx/conf.d/*.conf 2>/dev/null',
    'echo "=== Main nginx.conf ==="',
    'cat /etc/nginx/nginx.conf 2>/dev/null | head -80',
    'echo "=== Sites-enabled ==="',
    'ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "No sites-enabled"',
    'cat /etc/nginx/sites-enabled/* 2>/dev/null || true',
    'echo "=== Default HTML ==="',
    'ls /var/www/html/ 2>/dev/null',
    'head -30 /var/www/html/index.html 2>/dev/null || echo "No index.html"',
  ];

  var idx = 0;
  var output = '';
  function runNext() {
    if (idx >= cmds.length) {
      console.log(output);
      fixNginx();
      return;
    }
    conn.exec(cmds[idx++], function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() {
        output += o + '\n';
        runNext();
      });
    });
  }

  function fixNginx() {
    console.log('\n=== Fixing Nginx config ===');

    var newConfig = [
      'server {',
      '    listen 80 default_server;',
      '    server_name 118.31.164.41 _;',
      '',
      '    # CGCPT frontend',
      '    location /CGCPT {',
      '        alias /opt/CGCPT/web/dist;',
      '        index index.html;',
      '        try_files $uri $uri/ /CGCPT/index.html;',
      '    }',
      '',
      '    # CGCPT static assets',
      '    location /CGCPT/assets/ {',
      '        alias /opt/CGCPT/web/dist/assets/;',
      '        expires 30d;',
      '        add_header Cache-Control "public, immutable";',
      '    }',
      '',
      '    # CGCPT API proxy - FIXED: port 5001',
      '    location /CGCPT/api/ {',
      '        proxy_pass http://127.0.0.1:5001/api/;',
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
      '        proxy_pass http://127.0.0.1:5001/health;',
      '        proxy_set_header Host $host;',
      '    }',
      '',
      '    # CGCPT stacking API',
      '    location /CGCPT/stacking/ {',
      '        proxy_pass http://127.0.0.1:5001/stacking/;',
      '        proxy_set_header Host $host;',
      '        proxy_set_header X-Real-IP $remote_addr;',
      '    }',
      '',
      '    # CGCPT import API',
      '    location /CGCPT/import/ {',
      '        proxy_pass http://127.0.0.1:5001/import/;',
      '        proxy_set_header Host $host;',
      '        proxy_set_header X-Real-IP $remote_addr;',
      '        client_max_body_size 50m;',
      '    }',
      '',
      '    # CGCPT generate API',
      '    location /CGCPT/generate/ {',
      '        proxy_pass http://127.0.0.1:5001/generate/;',
      '        proxy_set_header Host $host;',
      '        proxy_set_header X-Real-IP $remote_addr;',
      '    }',
      '',
      '    # CGCPT other API routes',
      '    location /CGCPT/verify-topology {',
      '        proxy_pass http://127.0.0.1:5001/verify-topology;',
      '        proxy_set_header Host $host;',
      '    }',
      '',
      '    # SmartAgriculture frontend',
      '    location /smart {',
      '        alias /opt/smartagriculture/admin-platform/frontend/dist;',
      '        index index.html;',
      '        try_files $uri $uri/ /smart/index.html;',
      '    }',
      '',
      '    location /smart/assets/ {',
      '        alias /opt/smartagriculture/admin-platform/frontend/dist/assets/;',
      '        expires 30d;',
      '    }',
      '',
      '    # SmartAgriculture API',
      '    location /smart/api/ {',
      '        proxy_pass http://127.0.0.1:8000/api/;',
      '        proxy_set_header Host $host;',
      '        proxy_set_header X-Real-IP $remote_addr;',
      '    }',
      '',
      '    # Default root - show landing page',
      '    location = / {',
      '        return 302 /CGCPT/;',
      '    }',
      '',
      '    # Other static files',
      '    location / {',
      '        root /var/www/html;',
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
        console.log('Written cgcpt.conf');

        conn.exec("rm -f /etc/nginx/sites-enabled/default 2>/dev/null; echo 'cleaned default site'", function(e, st) {
          var o = '';
          st.on('data', function(d) { o += d.toString(); });
          st.on('close', function() {
            console.log(o.trim());

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
                      console.log('Nginx reloaded');
                      restartGunicorn();
                    });
                  });
                } else {
                  console.log('Nginx test FAILED');
                  restartGunicorn();
                }
              });
            });
          });
        });
      });
    });
  }

  function restartGunicorn() {
    console.log('\n=== Restarting Gunicorn ===');

    var cmds = [
      'systemctl restart cgcpt 2>&1',
      'sleep 2',
      'systemctl status cgcpt 2>&1 | head -15',
      'curl -s http://127.0.0.1:5001/health 2>&1',
      'systemctl restart cgcpt-worker 2>&1',
      'sleep 1',
      'systemctl status cgcpt-worker 2>&1 | head -10',
    ];

    var idx = 0;
    function runNext() {
      if (idx >= cmds.length) {
        verify();
        return;
      }
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
  }

  function verify() {
    console.log('\n=== Final Verification ===');
    var http = require('http');

    function checkURL(urlPath, label, ua, callback) {
      var opts = {
        hostname: '118.31.164.41', port: 80, path: urlPath, timeout: 8000,
        headers: { 'User-Agent': ua }
      };
      http.get(opts, function(res) {
        var d = [];
        res.on('data', function(c) { d.push(c); });
        res.on('end', function() {
          var body = Buffer.concat(d).toString('utf-8');
          var hasAIClub = body.indexOf('AIClub') >= 0;
          var hasCGCPT = body.indexOf('CGCPT') >= 0 || body.indexOf('cgcpt') >= 0;
          console.log(label + ': HTTP ' + res.statusCode + ' ' + body.length + 'B' +
            (hasAIClub ? ' [AIClub DETECTED!]' : '') +
            (hasCGCPT ? ' [CGCPT OK]' : ''));
          callback();
        });
      }).on('error', function(err) {
        console.log(label + ': ERROR - ' + err.message);
        callback();
      });
    }

    var mobileUA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1';
    var desktopUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';

    checkURL('/CGCPT/', 'Mobile /CGCPT/', mobileUA, function() {
      checkURL('/CGCPT/', 'Desktop /CGCPT/', desktopUA, function() {
        checkURL('/CGCPT/api/health', 'API health', mobileUA, function() {
          checkURL('/CGCPT/api/db/stats', 'API stats', desktopUA, function() {
            checkURL('/CGCPT/api/algorithms', 'API algorithms', desktopUA, function() {
              checkURL('/CGCPT/api/plugins', 'API plugins', desktopUA, function() {
                console.log('\n=== Deploy Complete ===');
                conn.end();
              });
            });
          });
        });
      });
    });
  }

  runNext();
});
conn.connect(config);
