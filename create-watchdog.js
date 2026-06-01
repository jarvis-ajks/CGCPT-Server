const { Client } = require('ssh2');

const host = '118.31.164.41';
const user = 'root';
const password = 'ZS1029384756!';

const watchdogScript = [
  '#!/bin/bash',
  '# CGCPT Health Watchdog - runs every 5 minutes via cron',
  '',
  'MAX_MEM_PERCENT=90',
  'RESTART_THRESHOLD=3',
  '',
  '# Check API health',
  'HEALTH=$(curl -sf http://127.0.0.1:5001/api/health 2>/dev/null)',
  'if [ -z "$HEALTH" ]; then',
  '    echo "$(date): API not responding, restarting cgcpt" >> /var/log/cgcpt_watchdog.log',
  '    systemctl restart cgcpt',
  '    exit 1',
  'fi',
  '',
  '# Check memory',
  'MEM_PERCENT=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get(\'memory\',{}).get(\'percent\',0))" 2>/dev/null)',
  'if [ -n "$MEM_PERCENT" ] && [ "$MEM_PERCENT" -gt "$MAX_MEM_PERCENT" ]; then',
  '    echo "$(date): Memory at ${MEM_PERCENT}%, restarting cgcpt" >> /var/log/cgcpt_watchdog.log',
  '    systemctl restart cgcpt',
  '    exit 1',
  'fi',
  '',
  '# Rotate watchdog log if too big',
  'if [ -f /var/log/cgcpt_watchdog.log ] && [ $(stat -f%z /var/log/cgcpt_watchdog.log 2>/dev/null || stat -c%s /var/log/cgcpt_watchdog.log 2>/dev/null) -gt 1048576 ]; then',
  '    tail -100 /var/log/cgcpt_watchdog.log > /var/log/cgcpt_watchdog.log.tmp',
  '    mv /var/log/cgcpt_watchdog.log.tmp /var/log/cgcpt_watchdog.log',
  'fi'
].join('\n');

const cmd = `cat > /opt/CGCPT/watchdog.sh << 'WATCHDOG_EOF'
${watchdogScript}
WATCHDOG_EOF
chmod +x /opt/CGCPT/watchdog.sh && echo "watchdog.sh created OK" && cat /opt/CGCPT/watchdog.sh`;

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
