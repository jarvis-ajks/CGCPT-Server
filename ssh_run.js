const { Client } = require('ssh2');
const conn = new Client();

const commands = process.argv.slice(2).join(' ');

conn.on('ready', () => {
  conn.exec(commands, (err, stream) => {
    if (err) { console.error(err); process.exit(1); }
    let stdout = '', stderr = '';
    stream.on('data', (data) => { stdout += data; process.stdout.write(data); });
    stream.stderr.on('data', (data) => { stderr += data; process.stderr.write(data); });
    stream.on('close', (code) => { conn.end(); process.exit(code); });
  });
}).connect({
  host: '118.31.164.41',
  port: 22,
  username: 'root',
  password: 'ZS1029384756!',
  readyTimeout: 15000
});
