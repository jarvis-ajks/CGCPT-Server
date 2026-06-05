# 贡献指南 / Contributing Guide

感谢您对 CGCPT 项目的关注！本文档将帮助您了解如何参与项目贡献。

---

## 行为准则 / Code of Conduct

### 我们的承诺 / Our Pledge

为了营造一个开放和友好的环境，我们作为贡献者和维护者承诺：无论年龄、体型、残疾、种族、性别认同和表达、经验水平、教育程度、社会经济地位、国籍、外貌、种族、宗教或性取向如何，参与我们的项目和社区都将为每个人提供无骚扰的体验。

### 不可接受的行为 / Unacceptable Behavior

- 使用性化的语言或图像
- 人身攻击或侮辱性评论
- 骚扰，无论公开还是私下
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

### 报告 / Reporting

如遇不当行为，请通过 GitHub Issues 或项目邮箱报告。

---

## 如何报告 Bug / How to Report Bugs

### 提交前检查

1. 搜索 [已有 Issues](https://github.com/cgcpt/cgcpt-server/issues) 确认未被报告
2. 确认您使用的是最新版本
3. 收集以下信息：
   - 操作系统和版本
   - Python / Node.js 版本
   - 复现步骤
   - 预期行为 vs 实际行为
   - 相关日志 / 错误信息

### Bug 报告模板

```markdown
## Bug 描述

简要描述问题

## 复现步骤

1. ...
2. ...
3. ...

## 预期行为

描述您期望发生的行为

## 实际行为

描述实际发生的行为

## 环境信息

- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.12.0]
- Node.js: [e.g. 18.17.0]
- 浏览器: [e.g. Chrome 120]

## 日志 / 截图

如有相关日志或截图，请附上
```

---

## 如何建议新功能 / How to Suggest Features

### 功能请求模板

```markdown
## 功能描述

清晰描述您希望添加的功能

## 使用场景

描述该功能解决的具体问题或使用场景

## 建议的实现方式

如果您有实现思路，请描述

## 替代方案

您考虑过的其他替代方案

## 附加信息

其他有助于理解需求的信息
```

### 功能请求原则

- 一个 Issue 只描述一个功能
- 说明功能的使用场景和价值
- 考虑与现有功能的兼容性
- 评估实现复杂度

---

## 开发环境搭建 / Development Setup

### 后端开发环境

```bash
# 1. Fork 并克隆项目
git clone https://github.com/YOUR_USERNAME/cgcpt-server.git
cd cgcpt-server

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装开发依赖
pip install -r requirements.txt
pip install pytest flake8 mypy black isort

# 4. 启动开发服务器
python api_server.py
```

### 前端开发环境

```bash
# 1. 进入前端目录
cd web

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

### 数据库设置（可选）

```bash
# MySQL 创建数据库
mysql -u root -p -e "CREATE DATABASE cgcpt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行迁移
python -c "from models import init_db; init_db()"

# 从文件系统导入数据
curl -X POST http://localhost:5000/api/db/migrate
```

---

## 编码规范 / Coding Standards

### Python 代码规范

#### PEP 8

所有 Python 代码必须遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范。

```bash
# 使用 flake8 检查
flake8 --max-line-length=120 --exclude=venv,_archive .

# 使用 black 自动格式化
black --line-length=120 .

# 使用 isort 排序 import
isort --profile=black .
```

#### 类型提示 (Type Hints)

所有新增函数必须添加类型提示：

```python
# 正确 ✓
def parse_cif_file(cif_path: Path) -> dict | None:
    """解析 CIF 文件并返回结构数据"""
    ...

# 错误 ✗
def parse_cif_file(cif_path):
    ...
```

#### 文档字符串 (Docstrings)

使用 Google 风格的 docstring：

```python
def generate_structure(layer_modes: list[str], stack_sequence: str = "ABC") -> dict:
    """生成层状晶体结构

    Args:
        layer_modes: 层模式列表，如 ["XO3", "M7", "XO3"]
        stack_sequence: 堆垛序列，如 "ABC"

    Returns:
        包含结构信息的字典，包括 lattice、atom_sites、topology 等

    Raises:
        ValueError: 当 layer_modes 为空时
        RuntimeError: 当 stack_main 模块未安装时
    """
    ...
```

#### 命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| 模块 | snake_case | `stacking_analyzer.py` |
| 类 | PascalCase | `LayeredXOGenerator` |
| 函数/方法 | snake_case | `parse_cif_file()` |
| 常量 | UPPER_SNAKE_CASE | `DATABASE_DIR` |
| 私有方法 | _leading_underscore | `_build_indexes()` |

### TypeScript / React 代码规范

```bash
# ESLint 检查
cd web && npm run lint

# TypeScript 类型检查
cd web && npx tsc --noEmit
```

#### 组件规范

- 使用函数式组件 + Hooks
- 使用 TypeScript 严格模式
- 组件文件名使用 PascalCase
- 工具函数文件名使用 camelCase

---

## Git 工作流 / Git Workflow

### 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 功能开发 | `feat/<description>` | `feat/stacking-bayesian` |
| Bug 修复 | `fix/<description>` | `fix/cif-parse-encoding` |
| 文档更新 | `docs/<description>` | `docs/api-endpoints` |
| 重构 | `refactor/<description>` | `refactor/cache-layer` |
| 性能优化 | `perf/<description>` | `perf/index-building` |
| 测试 | `test/<description>` | `test/stacking-predict` |

### Commit 消息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type 列表

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（不新增功能、不修复 Bug） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖更新 |
| `ci` | CI 配置 |

#### 示例

```
feat(stacking): 添加贝叶斯超参优化支持

实现了基于 scikit-optimize 的贝叶斯超参搜索，
替代原有网格搜索，训练速度提升 3x。

Closes #42
```

```
fix(cif): 修复非 UTF-8 编码 CIF 文件解析失败的问题

添加 errors='ignore' 参数处理非标准编码文件，
同时增加手动正则解析作为 fallback。
```

### 工作流程

```
1. 从 main 创建功能分支
   git checkout -b feat/my-feature

2. 开发并提交
   git add <files>
   git commit -m "feat(scope): 描述"

3. 保持与 main 同步
   git fetch origin
   git rebase origin/main

4. 推送到 Fork
   git push origin feat/my-feature

5. 创建 Pull Request
```

---

## Pull Request 流程 / Pull Request Process

### 提交前检查清单

- [ ] 代码通过 `flake8` 检查
- [ ] 代码通过 `black` 格式化
- [ ] 类型提示完整
- [ ] Docstring 完整
- [ ] 新功能有对应测试
- [ ] 无硬编码密码或密钥
- [ ] 无不必要的 `print()` 语句
- [ ] API 变更已更新文档

### PR 模板

```markdown
## 变更描述

简要描述本 PR 的变更内容

## 变更类型

- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 性能优化 (perf)
- [ ] 测试 (test)

## 关联 Issue

Closes #

## 测试

描述如何测试本变更

## 截图

如有 UI 变更，请附截图
```

### PR 审查流程

1. **自动检查** — CI 运行 lint、type check、测试
2. **代码审查** — 至少一位维护者审查
3. **修改** — 根据审查意见修改
4. **合并** — 审查通过后由维护者合并

---

## 代码审查清单 / Code Review Checklist

### 功能正确性

- [ ] 逻辑正确，边界条件已处理
- [ ] 错误处理完善，异常信息有意义
- [ ] 返回值格式与 API 文档一致

### 代码质量

- [ ] 遵循 PEP 8 / ESLint 规范
- [ ] 无重复代码
- [ ] 命名清晰、有意义
- [ ] 函数职责单一，长度合理

### 安全性

- [ ] 无 SQL 注入风险
- [ ] 无 XSS 风险
- [ ] 敏感信息未硬编码
- [ ] 文件上传有类型和大小限制

### 性能

- [ ] 无 N+1 查询
- [ ] 大数据量操作有分页/流式处理
- [ ] 缓存策略合理
- [ ] 无内存泄漏风险

### 兼容性

- [ ] API 变更向后兼容
- [ ] 数据库迁移脚本完整
- [ ] 前端类型定义已更新

---

## 开发提示 / Development Tips

### 调试 API

```bash
# 启动 Flask debug 模式
FLASK_ENV=development python api_server.py

# 查看详细日志
journalctl -u cgcpt -f
```

### 测试

```bash
# 运行系统测试
python test_system.py

# 测试 API 端点
curl http://localhost:5000/api/health
curl http://localhost:5000/api/stats
```

### 数据库操作

```bash
# 备份数据
python data_tools.py backup

# 导出材料
python data_tools.py export materials
```

---

感谢您的贡献！每一个 PR、Issue 和建议都让 CGCPT 变得更好。
