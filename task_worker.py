import importlib
import json
import time
import uuid
import traceback
from pathlib import Path
from datetime import datetime

from celery import Celery
from models import SessionLocal, Task, Algorithm, ModelArtifact

CELERY_BROKER = "redis://127.0.0.1:6379/0"
CELERY_BACKEND = "redis://127.0.0.1:6379/1"

celery_app = Celery(
    "cgcpt_worker",
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

BUILTIN_ALGORITHMS = [
    {
        "id": "stacking_train",
        "name": "堆垛识别训练",
        "description": "从数据库CIF文件训练决策树模型，识别材料拓扑类型",
        "algorithm_type": "training",
        "entry_point": "stacking_analyzer.train_decision_tree",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_ratio": {"type": "number", "default": 0.2, "description": "测试集比例"},
                "n_iterations": {"type": "integer", "default": 10, "description": "迭代次数"},
                "cv_folds": {"type": "integer", "default": 5, "description": "交叉验证折数"},
                "max_depth": {
                    "type": ["integer", "null"],
                    "default": None,
                    "description": "决策树最大深度",
                },
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string"},
                "test_accuracy": {"type": "number"},
                "cv_mean": {"type": "number"},
            },
        },
        "default_config": {"test_ratio": 0.2, "n_iterations": 10, "cv_folds": 5},
    },
    {
        "id": "stacking_predict",
        "name": "堆垛识别预测",
        "description": "使用已训练模型预测CIF文件的拓扑类型",
        "algorithm_type": "prediction",
        "entry_point": "stacking_analyzer.predict_stacking",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string", "description": "模型ID"},
                "cif_content": {"type": "string", "description": "CIF文件内容"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "predicted_topology": {"type": "string"},
                "confidence": {"type": "number"},
            },
        },
    },
    {
        "id": "structure_generate",
        "name": "结构生成",
        "description": "基于层组合规则生成新的钙钛矿结构",
        "algorithm_type": "generation",
        "entry_point": "stack_main.generate_structure",
        "input_schema": {
            "type": "object",
            "properties": {
                "layers": {"type": "array", "description": "层组合序列"},
                "space_group": {"type": "string", "description": "目标空间群"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "cif_content": {"type": "string"},
                "topology": {"type": "string"},
            },
        },
    },
    {
        "id": "topology_verify",
        "name": "拓扑验证",
        "description": "验证材料的拓扑分类是否正确",
        "algorithm_type": "verification",
        "entry_point": "verify_topology.verify",
        "input_schema": {
            "type": "object",
            "properties": {
                "cif_content": {"type": "string"},
                "expected_topology": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "verified": {"type": "boolean"},
                "details": {"type": "object"},
            },
        },
    },
    {
        "id": "import_cif",
        "name": "CIF数据导入",
        "description": "解析CIF文件并导入到数据库，自动归类拓扑",
        "algorithm_type": "import",
        "entry_point": "api_server._import_cif_batch",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "description": "CIF文件列表"},
                "topology": {"type": "string", "description": "指定拓扑分类"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "imported": {"type": "integer"},
                "skipped": {"type": "integer"},
                "errors": {"type": "integer"},
            },
        },
    },
]


def register_builtin_algorithms(db=None):
    if db is None:
        db = SessionLocal()
    try:
        for algo_def in BUILTIN_ALGORITHMS:
            existing = db.query(Algorithm).filter_by(id=algo_def["id"]).first()
            if existing:
                existing.name = algo_def["name"]
                existing.description = algo_def["description"]
                existing.entry_point = algo_def["entry_point"]
                existing.input_schema = algo_def.get("input_schema")
                existing.output_schema = algo_def.get("output_schema")
                existing.default_config = algo_def.get("default_config")
                existing.algorithm_type = algo_def.get("algorithm_type", "general")
            else:
                algo = Algorithm(
                    id=algo_def["id"],
                    name=algo_def["name"],
                    description=algo_def.get("description", ""),
                    version=algo_def.get("version", "1.0.0"),
                    algorithm_type=algo_def.get("algorithm_type", "general"),
                    entry_point=algo_def["entry_point"],
                    input_schema=algo_def.get("input_schema"),
                    output_schema=algo_def.get("output_schema"),
                    config_schema=algo_def.get("config_schema"),
                    default_config=algo_def.get("default_config"),
                )
                db.add(algo)
        db.commit()
    finally:
        if db is None:
            db.close()


def register_external_algorithm(algo_def: dict, db=None):
    if db is None:
        db = SessionLocal()
    try:
        required = ["id", "name", "entry_point"]
        for r in required:
            if r not in algo_def:
                raise ValueError(f"Missing required field: {r}")

        existing = db.query(Algorithm).filter_by(id=algo_def["id"]).first()
        if existing:
            for k, v in algo_def.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
        else:
            algo = Algorithm(**{k: v for k, v in algo_def.items() if hasattr(Algorithm, k)})
            db.add(algo)
        db.commit()
        return algo_def["id"]
    finally:
        if db is None:
            db.close()


def _resolve_entry_point(entry_point: str):
    parts = entry_point.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid entry_point format: {entry_point}. Expected 'module.function'")
    module_path, func_name = parts
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func


@celery_app.task(bind=True, name="cgcpt.execute_algorithm")
def execute_algorithm_task(self, task_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            return {"error": f"Task {task_id} not found"}

        task.status = "running"
        task.started_at = datetime.utcnow()
        task.celery_task_id = self.request.id
        db.commit()

        algorithm = db.query(Algorithm).filter_by(id=task.algorithm_id).first()
        if not algorithm:
            task.status = "failed"
            task.error_message = f"Algorithm {task.algorithm_id} not found"
            db.commit()
            return {"error": task.error_message}

        func = _resolve_entry_point(algorithm.entry_point)
        input_data = task.input_data or {}

        if algorithm.id == "stacking_train":
            from stacking_analyzer import scan_database_cifs, train_decision_tree

            samples = scan_database_cifs()

            def progress_cb(info):
                try:
                    task.progress = info.get("config_idx", 0) / max(info.get("total_steps", 1), 1)
                    task.progress_message = info.get("current_model", "")
                    db.commit()
                except Exception:
                    pass

            params = {**algorithm.default_config, **input_data}
            result = train_decision_tree(
                samples,
                test_ratio=params.get("test_ratio", 0.2),
                n_iterations=params.get("n_iterations", 10),
                cv_folds=params.get("cv_folds", 5),
                max_depth=params.get("max_depth"),
                progress_callback=progress_cb,
            )

            if result.get("success"):
                task.output_data = result
                task.status = "completed"
                task.progress = 1.0

                if result.get("model_id"):
                    artifact = ModelArtifact(
                        id=result["model_id"],
                        algorithm_id=algorithm.id,
                        task_id=task.id,
                        name=f"DecisionTree_{result['model_id']}",
                        model_type="dt",
                        metrics={
                            "test_accuracy": result["best_params"]["test_accuracy"],
                            "cv_mean": result["best_params"]["cv_mean"],
                            "cv_std": result["best_params"]["cv_std"],
                        },
                        feature_keys=result.get("feature_keys"),
                    )
                    db.add(artifact)
            else:
                task.status = "failed"
                task.error_message = result.get("error", "Unknown error")

        elif algorithm.id == "stacking_predict":
            from stacking_analyzer import predict_stacking, parse_cif_file
            import tempfile, os

            cif_content = input_data.get("cif_content", "")
            model_id = input_data.get("model_id", "")

            with tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w") as tmp:
                tmp.write(cif_content)
                tmp_path = tmp.name

            try:
                cif_data = parse_cif_file(Path(tmp_path))
                result = predict_stacking(model_id, cif_data)
            finally:
                os.unlink(tmp_path)

            if result.get("success"):
                task.output_data = result
                task.status = "completed"
                task.progress = 1.0
            else:
                task.status = "failed"
                task.error_message = result.get("error", "Prediction failed")

        else:
            try:
                from cgcpt_plugin import instantiate_plugin, CGCPTPlugin

                plugin_instance = instantiate_plugin(algorithm.id)
            except Exception:
                plugin_instance = None

            if plugin_instance is not None:

                def progress_cb(info):
                    try:
                        task.progress = info.get("progress", task.progress)
                        task.progress_message = info.get("message", "")
                        db.commit()
                    except Exception:
                        pass

                result = plugin_instance.run(
                    input_data,
                    task_id=task_id,
                    progress_callback=progress_cb,
                )
                task.output_data = result
                if result.get("success"):
                    task.status = "completed"
                    task.progress = 1.0
                else:
                    task.status = "failed"
                    task.error_message = result.get("error", "Plugin execution failed")
            else:
                result = func(**input_data)
                task.output_data = result if isinstance(result, dict) else {"result": str(result)}
                task.status = "completed"
                task.progress = 1.0

        task.completed_at = datetime.utcnow()
        db.commit()
        return task.output_data

    except Exception as e:
        try:
            task = db.query(Task).filter_by(id=task_id).first()
            if task:
                task.status = "failed"
                task.error_message = (
                    f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()[:2000]}"
                )
                task.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


def submit_task(algorithm_id: str, input_data: dict, created_by: str = "system") -> str:
    db = SessionLocal()
    try:
        algo = db.query(Algorithm).filter_by(id=algorithm_id, is_active=True).first()
        if not algo:
            raise ValueError(f"Algorithm {algorithm_id} not found or inactive")

        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            algorithm_id=algorithm_id,
            input_data=input_data,
            created_by=created_by,
        )
        db.add(task)
        db.commit()

        execute_algorithm_task.delay(task_id)
        return task_id
    finally:
        db.close()


def get_task_status(task_id: str) -> dict:
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            return {"error": "Task not found"}

        result = {
            "task_id": task.id,
            "algorithm_id": task.algorithm_id,
            "status": task.status,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

        if task.status == "running" and task.celery_task_id:
            try:
                async_result = celery_app.AsyncResult(task.celery_task_id)
                if async_result.state == "PROGRESS":
                    result["progress"] = async_result.info.get("current", 0) / max(
                        async_result.info.get("total", 1), 1
                    )
                    result["progress_message"] = async_result.info.get("description", "")
            except Exception:
                pass

        return result
    finally:
        db.close()
