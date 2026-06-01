const { Client } = require('ssh2');

const host = '118.31.164.41';
const user = 'root';
const password = 'ZS1029384756!';

const cmd = `sed -i 's/proxy_set_header Host System.Management.Automation.Internal.Host.InternalHost;/proxy_set_header Host \\$host;/' /etc/nginx/sites-available/ai-website && echo "FIXED" && grep -A 5 'api/health' /etc/nginx/sites-available/ai-website && nginx -t 2>&1 && systemctl reload nginx 2>&1 && echo "nginx reloaded OK"`;

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
