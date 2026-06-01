
import subprocess
import time
import sys

def run_cmd(cmd):
    print(f'执行命令: {cmd[:100]}...')
    result = subprocess.run(
        ['python', 'ssh_run_key.py', cmd],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    print(result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr)
    print(f'退出码: {result.returncode}\n')
    return result.returncode == 0

# Step 1: 执行数据库迁移
print('=' * 60)
print('Step 1: 执行数据库迁移')
print('=' * 60)

step1_cmd = '''cd /opt/CGCPT && /opt/CGCPT/venv/bin/python3 -c "
from models import init_db, SessionLocal, migrate_from_filesystem, Material, Prototype, Algorithm, Task
init_db()
print('✓ 数据库表初始化成功')
print('')
print('开始从文件系统迁移数据...')
result = migrate_from_filesystem(SessionLocal())
print('')
print('迁移完成！')
print('  - 导入原型:', result.get('imported_prototypes', 0))
print('  - 导入材料:', result.get('imported_materials', 0))
print('  - 错误数:', result.get('total_errors', 0))
if result.get('errors'):
    print('  错误示例:', str(result.get('errors')[:3]))
print('')

db = SessionLocal()
print('当前数据库统计:')
print('  - Prototype:', db.query(Prototype).count())
print('  - Material:', db.query(Material).count())
print('  - Algorithm:', db.query(Algorithm).count())
print('  - Task:', db.query(Task).count())
db.close()
" 2>&1'''

run_cmd(step1_cmd)

# Step 2: 验证迁移结果
print('=' * 60)
print('Step 2: 验证迁移结果')
print('=' * 60)

step2_cmd = 'curl -s http://localhost/CGCPT/api/db/status | python3 -m json.tool'
run_cmd(step2_cmd)

# Step 3: 测试提交一个训练任务
print('=' * 60)
print('Step 3: 测试提交一个训练任务')
print('=' * 60)

step3_cmd = '''curl -X POST -H 'Content-Type: application/json' -d '{
  "algorithm_id": "stacking_train",
  "input_data": {
    "test_ratio": 0.2,
    "n_iterations": 1,
    "cv_folds": 2
  }
}' http://localhost/CGCPT/api/tasks | python3 -m json.tool'''

run_cmd(step3_cmd)

# Step 4: 等待3秒后查看任务
print('=' * 60)
print('Step 4: 等待3秒后查看任务列表')
print('=' * 60)

time.sleep(3)

step4_cmd = "curl -s 'http://localhost/CGCPT/api/tasks?limit=10' | python3 -m json.tool"
run_cmd(step4_cmd)

print('=' * 60)
print('所有步骤执行完成')
print('=' * 60)
