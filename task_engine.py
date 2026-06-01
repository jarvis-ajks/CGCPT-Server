"""
CGCPT 任务执行引擎
提供任务状态管理辅助函数，供 task_worker.py 使用
"""

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/opt/CGCPT/logs")
try:
    LOG_DIR.mkdir(exist_ok=True)
except Exception:
    pass

logger = logging.getLogger("cgcpt.task_engine")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def update_task_progress(db, task_id: str, progress: float, message: str = ""):
    from models import Task
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.progress = max(0.0, min(1.0, progress))
            task.progress_message = message[:512] if message else ""
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update task progress [{task_id}]: {e}")


def set_task_status(db, task_id: str, status: str, error_msg: str = None, output_data: dict = None):
    from models import Task
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            if status == "completed":
                task.completed_at = datetime.utcnow()
                task.progress = 1.0
            if error_msg:
                task.error_message = error_msg[:4000]
            if output_data is not None:
                task.output_data = output_data
            db.commit()
    except Exception as e:
        logger.error(f"Failed to set task status [{task_id}]: {e}")


def create_model_artifact(db, model_id: str, algorithm_id: str, task_id: str,
                          model_type: str, metrics: dict, feature_keys: list = None,
                          name: str = None, file_path: str = None):
    from models import ModelArtifact
    try:
        existing = db.query(ModelArtifact).filter_by(id=model_id).first()
        if existing:
            logger.info(f"Model artifact {model_id} already exists, skipping")
            return True
        artifact = ModelArtifact(
            id=model_id,
            algorithm_id=algorithm_id,
            task_id=task_id,
            name=name or f"{algorithm_id}_{model_id}",
            model_type=model_type,
            metrics=metrics,
            feature_keys=feature_keys,
            file_path=file_path,
        )
        db.add(artifact)
        db.commit()
        logger.info(f"Created model artifact: {model_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create model artifact: {e}")
        db.rollback()
        return False
