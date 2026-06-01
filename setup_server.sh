#!/bin/bash
# CGCPT 堆垛特征识别 - 服务器一键部署脚本
# 用法: bash setup_server.sh
# 前提: Ubuntu/Debian服务器, 有sudo权限

set -e

echo "============================================================"
echo "  CGCPT 堆垛特征识别 - 服务器环境配置"
echo "============================================================"

INSTALL_DIR="${HOME}/cgcpt-stacking"
DATA_DIR="${INSTALL_DIR}/data"
MODEL_DIR="${INSTALL_DIR}/models"

echo ""
echo "安装目录: ${INSTALL_DIR}"
echo "数据目录: ${DATA_DIR}  (将CIF文件按类别放入子文件夹)"
echo "模型目录: ${MODEL_DIR}"
echo ""

# 1. Install Python & pip
echo "[1/5] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "  安装Python3..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo "  ${PYTHON_VERSION}"

# 2. Create venv
echo ""
echo "[2/5] 创建虚拟环境..."
if [ ! -d "${INSTALL_DIR}/venv" ]; then
    python3 -m venv "${INSTALL_DIR}/venv"
fi
echo "  虚拟环境: ${INSTALL_DIR}/venv"

# 3. Install dependencies
echo ""
echo "[3/5] 安装Python依赖..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip -q
"${INSTALL_DIR}/venv/bin/pip" install pymatgen scikit-learn joblib numpy -q
echo "  依赖安装完成"

# 4. Copy source files
echo ""
echo "[4/5] 复制源代码..."
mkdir -p "${INSTALL_DIR}" "${DATA_DIR}" "${MODEL_DIR}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -f "${SCRIPT_DIR}/stacking_analyzer.py" "${INSTALL_DIR}/"
cp -f "${SCRIPT_DIR}/train_oneclick.py" "${INSTALL_DIR}/"
cp -f "${SCRIPT_DIR}/predict_one.py" "${INSTALL_DIR}/"
echo "  源代码已复制"

# 5. Verify
echo ""
echo "[5/5] 验证安装..."
VALID=$("${INSTALL_DIR}/venv/bin/python" -c "
import stacking_analyzer
print('stacking_analyzer: OK')
print(f'  pymatgen: {stacking_analyzer.HAS_PYMATGEN}')
print(f'  sklearn: {stacking_analyzer.HAS_SKLEARN}')
" 2>&1)
echo "  ${VALID}"

echo ""
echo "============================================================"
echo "  ✅ 安装完成!"
echo "============================================================"
echo ""
echo "  使用方法:"
echo ""
echo "  1. 准备数据 (每个子文件夹=一个类别):"
echo "     mkdir -p ${DATA_DIR}/XO"
echo "     mkdir -p ${DATA_DIR}/XO2"
echo "     mkdir -p ${DATA_DIR}/XO3"
echo "     # 将CIF文件放入对应文件夹"
echo "     cp /path/to/XO_cifs/*.cif ${DATA_DIR}/XO/"
echo "     cp /path/to/XO2_cifs/*.cif ${DATA_DIR}/XO2/"
echo ""
echo "  2. 一键训练:"
echo "     cd ${INSTALL_DIR}"
echo "     ./venv/bin/python train_oneclick.py --data ${DATA_DIR}"
echo ""
echo "  3. 快速训练(测试用):"
echo "     ./venv/bin/python train_oneclick.py --data ${DATA_DIR} --quick"
echo ""
echo "  4. 完整训练(生产用):"
echo "     ./venv/bin/python train_oneclick.py --data ${DATA_DIR} --iterations 5 --cv-folds 5"
echo ""
echo "  5. 预测:"
echo "     ./venv/bin/python predict_one.py --model MODEL_ID --cif test.cif"
echo "     ./venv/bin/python predict_one.py --list-models"
echo ""
echo "============================================================"
