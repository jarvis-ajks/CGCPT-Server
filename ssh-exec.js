const { Client } = require('ssh2');

const host = process.argv[2];
const cmd = process.argv[3];
const user = process.argv[4] || 'root';
const password = process.argv[5] || 'ZS1029384756!';

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
