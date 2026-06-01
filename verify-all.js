const { Client } = require('ssh2');

const host = '118.31.164.41';
const user = 'root';
const password = 'ZS1029384756!';

const cmd = `echo "=== NGINX TEST ===" && nginx -t 2>&1 && echo "=== NGINX RELOAD ===" && systemctl reload nginx 2>&1 && echo "nginx reloaded OK" && echo "=== HEALTH CHECK ===" && curl -s http://localhost/CGCPT/api/health | python3 -m json.tool && echo "=== CRONTAB ===" && crontab -l && echo "=== WATCHDOG SCRIPT ===" && cat /opt/CGCPT/watchdog.sh && echo "=== LOGROTATE NGINX ===" && cat /etc/logrotate.d/cgcpt-nginx && echo "=== LOGROTATE APP ===" && cat /etc/logrotate.d/cgcpt-app`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    if (err) { console.error('EXEC_ERROR:', err.message); conn.end(); process.exit(1); }
    let stdout = '', stderr = '';
    stream.on('data', (data) => { stdout += data.toString(); });
    stream.stderr.on('data', (data) => { stderr += data.toString(); });
    stream.on('close', (code) => {
      if (stdout) process.stdout.write(stdout);
      if (stderr) process.stderr.write(stderr);
      conn.end();
      process.exit(code || 0);
    });
  });
}).on('error', (err) => {
  console.error('SSH_ERROR:', err.message);
  process.exit(1);
}).connect({ host, port: 22, username: user, password, readyTimeout: 30000 });
