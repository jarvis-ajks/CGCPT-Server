const { Client } = require('ssh2');

const host = '118.31.164.41';
const user = 'root';
const password = 'ZS1029384756!';

const cmd = `(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/CGCPT/watchdog.sh") | crontab - && echo "CRON ADDED" && crontab -l && echo "===GUNICORN===" && cat /opt/CGCPT/gunicorn.conf.py`;

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
