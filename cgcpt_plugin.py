"""
CGCPT Plugin SDK
提供完整的插件开发框架，包括基类、装饰器、上下文对象和工具函数

使用方式:
  1. 继承 CGCPTPlugin 基类
  2. 使用 @cgcpt_algorithm 装饰器注册算法
  3. 实现 execute() 方法
  4. 将文件放到 /opt/CGCPT/plugins/ 目录下
  5. 通过 API 或 CLI 注册插件

示例:
    from cgcpt_plugin import CGCPTPlugin, PluginContext, cgcpt_algorithm

    @cgcpt_algorithm(
        id="my_analyzer",
        name="My Analyzer",
        algorithm_type="prediction",
        description="分析材料结构",
    )
    class MyAnalyzer(CGCPTPlugin):
        def execute(self, ctx: PluginContext) -> dict:
            cif = ctx.get_cif()
            result = self.analyze(cif)
            ctx.save_material(result)
            return {"success": True, "analysis": result}
"""

import os
import sys
import json
import uuid
import logging
import traceback
import importlib
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("cgcpt.plugin_sdk")

_PLUGIN_REGISTRY: Dict[str, Dict[str, Any]] = {}


class PluginContext:
    """
    插件执行上下文
    提供数据库访问、进度更新、材料保存等能力
    """

    def __init__(
        self,
        input_data: Dict[str, Any],
        task_id: str = "",
        algorithm_id: str = "",
        progress_callback: Optional[Callable] = None,
    ):
        self._input_data = input_data
        self._task_id = task_id
        self._algorithm_id = algorithm_id
        self._progress_cb = progress_callback
        self._db = None
        self._logs: List[str] = []

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def algorithm_id(self) -> str:
        return self._algorithm_id

    @property
    def input_data(self) -> Dict[str, Any]:
        return self._input_data

    def get(self, key: str, default: Any = None) -> Any:
        return self._input_data.get(key, default)

    def require(self, key: str) -> Any:
        if key not in self._input_data:
            raise ValueError(f"缺少必需参数: {key}")
        return self._input_data[key]

    def get_cif(self) -> str:
        return self.require("cif_content")

    def get_cif_path(self) -> Optional[str]:
        return self._input_data.get("cif_path")

    def get_model_id(self) -> Optional[str]:
        return self._input_data.get("model_id")

    def get_db(self):
        if self._db is None:
            from models import SessionLocal

            self._db = SessionLocal()
        return self._db

    def close_db(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    def update_progress(self, progress: float, message: str = ""):
        if self._progress_cb:
            self._progress_cb({"progress": progress, "message": message})
        self._logs.append(
            f"[{datetime.utcnow().isoformat()}] progress={progress:.2f} msg={message}"
        )

    def log(self, message: str):
        self._logs.append(f"[{datetime.utcnow().isoformat()}] {message}")
        logger.info(f"[{self._task_id}] {message}")

    def save_material(
        self,
        material_id: str,
        formula: str,
        space_group: str,
        topology_id: str,
        elements: List[str],
        lattice: Dict[str, float],
        cif_content: str = "",
        is_verified: bool = False,
        source: str = "algorithm",
        metadata: Optional[Dict] = None,
        n_atoms: int = 0,
    ) -> bool:
        db = self.get_db()
        try:
            from models import Material

            existing = db.query(Material).filter_by(id=material_id).first()
            if existing:
                self.log(f"材料 {material_id} 已存在，跳过")
                return False

            mat = Material(
                id=material_id,
                formula=formula,
                space_group=space_group,
                topology_id=topology_id,
                elements=elements,
                lattice_a=lattice.get("a"),
                lattice_b=lattice.get("b"),
                lattice_c=lattice.get("c"),
                lattice_alpha=lattice.get("alpha"),
                lattice_beta=lattice.get("beta"),
                lattice_gamma=lattice.get("gamma"),
                n_atoms=n_atoms or len(elements),
                is_verified=is_verified,
                source=source,
                cif_content=cif_content,
                metadata_json=metadata,
            )
            db.add(mat)
            db.commit()
            self.log(f"已保存材料 {material_id} ({formula})")
            return True
        except Exception as e:
            db.rollback()
            self.log(f"保存材料失败: {e}")
            return False

    def save_model_artifact(
        self,
        model_id: str,
        model_type: str,
        metrics: Dict[str, Any],
        feature_keys: Optional[List[str]] = None,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        db = self.get_db()
        try:
            from models import ModelArtifact

            existing = db.query(ModelArtifact).filter_by(id=model_id).first()
            if existing:
                self.log(f"模型产物 {model_id} 已存在")
                return False

            artifact = ModelArtifact(
                id=model_id,
                algorithm_id=self._algorithm_id,
                task_id=self._task_id,
                name=name or f"{self._algorithm_id}_{model_id}",
                model_type=model_type,
                metrics=metrics,
                feature_keys=feature_keys,
                file_path=file_path,
            )
            db.add(artifact)
            db.commit()
            self.log(f"已保存模型产物 {model_id}")
            return True
        except Exception as e:
            db.rollback()
            self.log(f"保存模型产物失败: {e}")
            return False

    def query_materials(
        self, topology_id: Optional[str] = None, formula: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        db = self.get_db()
        try:
            from models import Material

            query = db.query(Material)
            if topology_id:
                query = query.filter_by(topology_id=topology_id)
            if formula:
                query = query.filter(Material.formula.like(f"%{formula}%"))
            materials = query.limit(limit).all()
            return [
                {
                    "id": m.id,
                    "formula": m.formula,
                    "space_group": m.space_group,
                    "topology_id": m.topology_id,
                    "elements": m.elements,
                    "is_verified": m.is_verified,
                    "n_atoms": m.n_atoms,
                }
                for m in materials
            ]
        except Exception as e:
            self.log(f"查询材料失败: {e}")
            return []

    def query_prototypes(self, crystal_system: Optional[str] = None) -> List[Dict]:
        db = self.get_db()
        try:
            from models import Prototype

            query = db.query(Prototype)
            if crystal_system:
                query = query.filter_by(crystal_system=crystal_system)
            protos = query.all()
            return [
                {
                    "id": p.id,
                    "prototype_id": p.prototype_id,
                    "ideal_space_group": p.ideal_space_group,
                    "crystal_system": p.crystal_system,
                }
                for p in protos
            ]
        except Exception as e:
            self.log(f"查询原型失败: {e}")
            return []

    def get_logs(self) -> List[str]:
        return self._logs.copy()


class CGCPTPlugin(ABC):
    """
    插件基类
    所有 CGCPT 插件必须继承此类并实现 execute() 方法
    """

    algorithm_id: str = ""
    algorithm_name: str = ""
    algorithm_type: str = "general"
    description: str = ""
    version: str = "1.0.0"
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    default_config: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, ctx: PluginContext) -> Dict[str, Any]:
        """
        插件执行入口

        Args:
            ctx: 插件执行上下文，提供输入数据、数据库访问、进度更新等

        Returns:
            dict: 执行结果，必须包含 "success" 字段
        """
        raise NotImplementedError

    def validate_input(self, ctx: PluginContext) -> Optional[str]:
        """
        验证输入参数
        返回 None 表示验证通过，返回字符串表示错误信息
        子类可覆盖此方法实现自定义验证
        """
        if not self.input_schema:
            return None

        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        for key in required:
            if key not in ctx.input_data:
                return f"缺少必需参数: {key}"

        for key, schema in properties.items():
            if key in ctx.input_data:
                value = ctx.input_data[key]
                expected_type = schema.get("type")
                if expected_type and expected_type != "null":
                    type_map = {
                        "string": str,
                        "integer": int,
                        "number": (int, float),
                        "boolean": bool,
                        "array": list,
                        "object": dict,
                    }
                    allowed = type_map.get(expected_type)
                    if allowed and not isinstance(value, allowed):
                        return f"参数 {key} 类型错误: 期望 {expected_type}, 实际 {type(value).__name__}"

        return None

    def get_definition(self) -> Dict[str, Any]:
        module_name = self.__class__.__module__
        class_name = self.__class__.__name__
        entry_point = f"{module_name}.{class_name}"

        return {
            "id": self.algorithm_id,
            "name": self.algorithm_name,
            "description": self.description,
            "version": self.version,
            "algorithm_type": self.algorithm_type,
            "entry_point": entry_point,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "default_config": self.default_config,
        }

    def run(
        self,
        input_data: Dict[str, Any],
        task_id: str = "",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        ctx = PluginContext(
            input_data=input_data,
            task_id=task_id,
            algorithm_id=self.algorithm_id,
            progress_callback=progress_callback,
        )
        try:
            validation_error = self.validate_input(ctx)
            if validation_error:
                return {"success": False, "error": validation_error}

            result = self.execute(ctx)

            if not isinstance(result, dict):
                result = {"success": True, "result": result}
            if "success" not in result:
                result["success"] = True

            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}",
                "traceback": traceback.format_exc()[:2000],
            }
        finally:
            ctx.close_db()


def cgcpt_algorithm(
    id: str,
    name: str,
    algorithm_type: str = "general",
    description: str = "",
    version: str = "1.0.0",
    input_schema: Optional[Dict] = None,
    output_schema: Optional[Dict] = None,
    default_config: Optional[Dict] = None,
):
    """
    算法注册装饰器

    用法:
        @cgcpt_algorithm(
            id="my_algo",
            name="My Algorithm",
            algorithm_type="prediction",
            description="描述",
        )
        class MyAlgo(CGCPTPlugin):
            def execute(self, ctx):
                ...
    """

    def decorator(cls: Type[CGCPTPlugin]) -> Type[CGCPTPlugin]:
        cls.algorithm_id = id
        cls.algorithm_name = name
        cls.algorithm_type = algorithm_type
        cls.description = description
        cls.version = version
        cls.input_schema = input_schema or {}
        cls.output_schema = output_schema or {}
        cls.default_config = default_config or {}

        _PLUGIN_REGISTRY[id] = {
            "class": cls,
            "definition": {
                "id": id,
                "name": name,
                "description": description,
                "version": version,
                "algorithm_type": algorithm_type,
                "entry_point": f"{cls.__module__}.{cls.__name__}",
                "input_schema": input_schema or {},
                "output_schema": output_schema or {},
                "default_config": default_config or {},
            },
        }

        return cls

    return decorator


def get_plugin_registry() -> Dict[str, Dict[str, Any]]:
    return _PLUGIN_REGISTRY.copy()


def discover_plugins(plugin_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    自动发现并加载 plugins/ 目录下的所有插件

    Args:
        plugin_dir: 插件目录路径，默认为 /opt/CGCPT/plugins

    Returns:
        发现的插件定义列表
    """
    if plugin_dir is None:
        plugin_dir = str(Path(__file__).parent / "plugins")

    plugin_path = Path(plugin_dir)
    if not plugin_path.exists():
        logger.info(f"插件目录不存在: {plugin_path}")
        return []

    if str(plugin_path) not in sys.path:
        sys.path.insert(0, str(plugin_path))

    discovered = []
    for py_file in sorted(plugin_path.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = py_file.stem
        try:
            importlib.import_module(module_name)
            logger.info(f"已加载插件模块: {module_name}")
        except Exception as e:
            logger.error(f"加载插件模块 {module_name} 失败: {e}")

    for algo_id, info in _PLUGIN_REGISTRY.items():
        discovered.append(info["definition"])
        logger.info(f"发现插件: {algo_id} - {info['definition']['name']}")

    return discovered


def instantiate_plugin(algo_id: str) -> Optional[CGCPTPlugin]:
    if algo_id in _PLUGIN_REGISTRY:
        cls = _PLUGIN_REGISTRY[algo_id]["class"]
        return cls()
    return None


def validate_plugin_class(cls: Type[CGCPTPlugin]) -> List[str]:
    """
    验证插件类是否符合规范

    Returns:
        错误列表，空列表表示验证通过
    """
    errors = []

    if not issubclass(cls, CGCPTPlugin):
        errors.append("必须继承 CGCPTPlugin 基类")

    if not cls.algorithm_id:
        errors.append("algorithm_id 不能为空")

    if not cls.algorithm_name:
        errors.append("algorithm_name 不能为空")

    if not cls.algorithm_type:
        errors.append("algorithm_type 不能为空")

    valid_types = {
        "training",
        "prediction",
        "generation",
        "validation",
        "verification",
        "import",
        "general",
    }
    if cls.algorithm_type not in valid_types:
        errors.append(f"algorithm_type '{cls.algorithm_type}' 不合法，可选: {valid_types}")

    if not issubclass(cls, CGCPTPlugin) or cls.execute is CGCPTPlugin.execute:
        errors.append("必须实现 execute() 方法")

    return errors
