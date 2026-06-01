var Client = require('ssh2').Client;
var config = { host: '118.31.164.41', port: 22, username: 'root', password: 'ZS1029384756!' };

var conn = new Client();
conn.on('ready', function() {
  console.log('Fixing Nginx CGCPT frontend config...\n');

  var cgcptSection = [
    '# ==========================================',
    '# CGCPT (/CGCPT/) - Crystal Structure Platform',
    '# ==========================================',
    '',
    '    location = /CGCPT/api/health {',
    '        proxy_pass http://127.0.0.1:5001/api/health;',
    '        proxy_set_header Host $host;',
    '        access_log off;',
    '    }',
    '',
    '    location /CGCPT/api/ {',
    '        proxy_pass http://127.0.0.1:5001/api/;',
    '        proxy_set_header Host $host;',
    '        proxy_set_header X-Real-IP $remote_addr;',
    '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;',
    '        proxy_set_header X-Forwarded-Proto $scheme;',
    '        proxy_connect_timeout 10s;',
    '        proxy_read_timeout 300s;',
    '        proxy_buffering off;',
    '    }',
    '',
    '    location /CGCPT/health {',
    '        proxy_pass http://127.0.0.1:5001/api/health;',
    '        proxy_set_header Host $host;',
    '    }',
    '',
    '    location ^~ /CGCPT/assets/ {',
    '        alias /opt/CGCPT/web/dist/assets/;',
    '        expires 365d;',
    '        add_header Cache-Control "public, immutable";',
    '        add_header X-Content-Type-Options "nosniff";',
    '        access_log off;',
    '    }',
    '',
    '    location ^~ /CGCPT/ {',
    '        alias /opt/CGCPT/web/dist/;',
    '        index index.html;',
    '        try_files $uri $uri/ /CGCPT/index.html;',
    '    }',
    '',
    '    location = /CGCPT {',
    '        return 301 /CGCPT/;',
    '    }',
  ].join('\n');

  var sedCmd = "python3 -c \"\n" +
    "import re\n" +
    "with open('/etc/nginx/sites-available/ai-website', 'r') as f:\n" +
    "    content = f.read()\n" +
    "new_cgcpt = '''" + cgcptSection.replace(/'/g, "\\'") + "'''\n" +
    "pattern = r'# ={10,}.*?# CGCPT.*?(?=\\n    # ={10,}|\\n    location = /hnc|\\Z)'\n" +
    "content = re.sub(pattern, new_cgcpt, content, flags=re.DOTALL)\n" +
    "with open('/etc/nginx/sites-available/ai-website', 'w') as f:\n" +
    "    f.write(content)\n" +
    "print('OK')\n" +
    "\"";

  conn.exec(sedCmd, function(e, st) {
    var o = '';
    st.on('data', function(d) { o += d.toString(); });
    st.stderr.on('data', function(d) { o += d.toString(); });
    st.on('close', function() {
      console.log('Python sed: ' + o.trim());

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
                setTimeout(function() { verify(); }, 2000);
              });
            });
          } else {
            console.log('FAILED - trying direct write');
            directWrite();
          }
        });
      });
    });
  });

  function directWrite() {
    var fullConfig = 'server {\n' +
      '    listen 80 default_server;\n' +
      '    server_name _ localhost;\n' +
      '    client_max_body_size 50M;\n' +
      '    gzip on;\n' +
      '    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;\n' +
      '    gzip_min_length 1024;\n' +
      '    gzip_comp_level 6;\n' +
      '\n' +
      cgcptSection + '\n' +
      '\n' +
      '    # HNC\n' +
      '    location /hnc/api/ { proxy_pass http://127.0.0.1:8000/api/; proxy_set_header Host $host; }\n' +
      '    location ^~ /hnc/assets/ { alias /hnc/dist/assets/; expires 365d; }\n' +
      '    location ^~ /hnc/ { alias /hnc/dist/; index index.html; try_files $uri $uri/ /hnc/index.html; }\n' +
      '    location = /hnc { return 301 /hnc/; }\n' +
      '\n' +
      '    location = / { return 301 /AIclub/; }\n' +
      '\n' +
      '    # AI Club\n' +
      '    location ^~ /AIclub/js/ { root /opt/ai-club/frontend; expires 365d; }\n' +
      '    location ^~ /AIclub/css/ { root /opt/ai-club/frontend; expires 365d; }\n' +
      '    location = /AIclub/favicon.ico { root /opt/ai-club/frontend; }\n' +
      '    location ^~ /AIclub/auth/ { proxy_pass http://127.0.0.1:3031/auth/; proxy_set_header Host $host; }\n' +
      '    location ^~ /AIclub/enroll/ { proxy_pass http://127.0.0.1:3031/enroll/; proxy_set_header Host $host; }\n' +
      '    location = /AIclub/admin/login { root /opt/ai-club/frontend; try_files $uri /AIclub/index.html; }\n' +
      '    location = /AIclub/admin/dashboard { root /opt/ai-club/frontend; try_files $uri /AIclub/index.html; }\n' +
      '    location ^~ /AIclub/admin/ { proxy_pass http://127.0.0.1:3031/admin/; proxy_set_header Host $host; }\n' +
      '    location ^~ /AIclub/home/ { proxy_pass http://127.0.0.1:3031/home/; proxy_set_header Host $host; }\n' +
      '    location ^~ /AIclub/health { proxy_pass http://127.0.0.1:3031/health; proxy_set_header Host $host; }\n' +
      '    location ^~ /AIclub/uploads/ { proxy_pass http://127.0.0.1:3031/uploads/; proxy_set_header Host $host; }\n' +
      '    location ^~ /AIclub/ { root /opt/ai-club/frontend; try_files $uri $uri/ /AIclub/index.html; }\n' +
      '    location = /AIclub { return 301 /AIclub/; }\n' +
      '\n' +
      '    # PPT\n' +
      '    location ^~ /PPT/ws { proxy_pass http://127.0.0.1:8765; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; proxy_set_header Host $host; proxy_read_timeout 86400s; }\n' +
      '    location ^~ /PPT/ { alias /var/www/PPT/; index metaverse-slides.html; try_files $uri $uri/ /PPT/metaverse-slides.html; }\n' +
      '    location = /PPT { return 301 /PPT/; }\n' +
      '\n' +
      '    # Smart Agriculture\n' +
      '    location ^~ /smart/ws/ { proxy_pass http://127.0.0.1:8080/ws/; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; proxy_set_header Host $host; proxy_read_timeout 86400s; }\n' +
      '    location ^~ /smart/ { proxy_pass http://127.0.0.1:8080/; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_buffering off; }\n' +
      '    location = /smart { return 301 /smart/; }\n' +
      '\n' +
      '    # Wheel\n' +
      '    location ^~ /wheel/ { proxy_pass http://127.0.0.1:3005; proxy_set_header Host $host; }\n' +
      '    location = /wheel { return 301 /wheel/; }\n' +
      '\n' +
      '    # Legacy\n' +
      '    location / { root /opt/ai-website/frontend; index index.html; try_files $uri $uri/ /index.html; }\n' +
      '    location ~ ^/admin/(login|dashboard)$ { root /opt/ai-website/frontend; try_files $uri /index.html; }\n' +
      '    location /auth/ { proxy_pass http://127.0.0.1:3031/auth/; proxy_set_header Host $host; }\n' +
      '    location /enroll/ { proxy_pass http://127.0.0.1:3031/enroll/; proxy_set_header Host $host; }\n' +
      '    location /admin/ { proxy_pass http://127.0.0.1:3031/admin/; proxy_set_header Host $host; }\n' +
      '    location /home/ { proxy_pass http://127.0.0.1:3031/home/; proxy_set_header Host $host; }\n' +
      '    location /health { proxy_pass http://127.0.0.1:3031/health; proxy_set_header Host $host; }\n' +
      '    location /uploads/ { proxy_pass http://127.0.0.1:3031/uploads/; proxy_set_header Host $host; }\n' +
      '    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot)$ { root /opt/ai-website/frontend; expires 365d; try_files $uri =404; }\n' +
      '}\n';

    var writeCmd = "cat > /etc/nginx/sites-available/ai-website << 'NGINXEOF'\n" + fullConfig + "\nNGINXEOF";
    conn.exec(writeCmd, function(e, st) {
      var o = '';
      st.on('data', function(d) { o += d.toString(); });
      st.stderr.on('data', function(d) { o += d.toString(); });
      st.on('close', function() {
        console.log('Direct write done');

        conn.exec('nginx -t 2>&1', function(e, st) {
          var o = '';
          st.on('data', function(d) { o += d.toString(); });
          st.stderr.on('data', function(d) { o += d.toString(); });
          st.on('close', function() {
            console.log('Nginx test: ' + o.trim());
            if (o.indexOf('successful') >= 0) {
              conn.exec('nginx -s reload 2>&1', function(e, st) {
                var o = '';
                st.on('data', function(d) { o += d.toString(); });
                st.on('close', function() {
                  console.log('Nginx reloaded');
                  setTimeout(function() { verify(); }, 2000);
                });
              });
            } else {
              console.log('FAILED AGAIN');
              conn.end();
            }
          });
        });
      });
    });
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
          if (body.indexOf('AIClub') >= 0 || body.indexOf('AIclub') >= 0) tags.push('AIClub!');
          if (body.indexOf('CGCPT') >= 0 || body.indexOf('cgcpt') >= 0) tags.push('CGCPT');
          if (body.indexOf('success') >= 0) tags.push('API_OK');
          console.log(label + ': HTTP ' + res.statusCode + ' ' + body.length + 'B ' + (tags.length ? '[' + tags.join(',') + ']' : ''));
          cb();
        });
      }).on('error', function(err) {
        console.log(label + ': ERROR ' + err.message);
        cb();
      });
    }

    var mobile = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15';
    var desktop = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';

    check('/CGCPT/', 'Mobile /CGCPT/', mobile, function() {
      check('/CGCPT/', 'Desktop /CGCPT/', desktop, function() {
        check('/CGCPT/api/health', 'API health', mobile, function() {
          check('/CGCPT/api/db/stats', 'API stats', desktop, function() {
            check('/CGCPT/api/algorithms', 'API algos', desktop, function() {
              check('/CGCPT/api/plugins', 'API plugins', desktop, function() {
                check('/CGCPT/api/db/materials?page=1&page_size=5', 'API materials', desktop, function() {
                  check('/AIclub/', 'AIclub check', desktop, function() {
                    console.log('\n=== Done ===');
                    conn.end();
                  });
                });
              });
            });
          });
        });
      });
    });
  }
});
conn.connect(config);
