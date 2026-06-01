import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text, Boolean,
    DateTime, JSON, ForeignKey, Index, Enum as SAEnum, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.environ.get(
    "CGCPT_DB_URL",
    "mysql+pymysql://root@127.0.0.1:3306/cgcpt?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


class Prototype(Base):
    __tablename__ = "prototypes"

    id = Column(String(128), primary_key=True)
    prototype_id = Column(String(128), index=True)
    expanded_modes = Column(JSON)
    reference_grid = Column(String(64))
    ideal_space_group = Column(String(64))
    space_group_number = Column(Integer)
    crystal_system = Column(String(32))
    is_neutral = Column(Boolean)
    topology_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    materials = relationship("Material", back_populates="prototype")

    __table_args__ = (
        Index("ix_proto_crystal_system", "crystal_system"),
    )


class Material(Base):
    __tablename__ = "materials"

    id = Column(String(256), primary_key=True)
    formula = Column(String(128), index=True)
    space_group = Column(String(64), index=True)
    topology_id = Column(String(128), ForeignKey("prototypes.id"), index=True)
    elements = Column(JSON)
    lattice_a = Column(Float)
    lattice_b = Column(Float)
    lattice_c = Column(Float)
    lattice_alpha = Column(Float)
    lattice_beta = Column(Float)
    lattice_gamma = Column(Float)
    n_atoms = Column(Integer)
    is_verified = Column(Boolean, default=False)
    source = Column(String(32), default="raw")
    cif_path = Column(String(512))
    cif_content = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prototype = relationship("Prototype", back_populates="materials")

    __table_args__ = (
        Index("ix_mat_formula_sg", "formula", "space_group"),
        Index("ix_mat_verified", "is_verified"),
    )


class Algorithm(Base):
    __tablename__ = "algorithms"

    id = Column(String(128), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    version = Column(String(32), default="1.0.0")
    algorithm_type = Column(String(32), index=True)
    entry_point = Column(String(256), nullable=False)
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    config_schema = Column(JSON, nullable=True)
    default_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="algorithm")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(128), primary_key=True)
    algorithm_id = Column(String(128), ForeignKey("algorithms.id"), index=True)
    status = Column(
        SAEnum("pending", "running", "completed", "failed", "cancelled", name="task_status"),
        default="pending", index=True
    )
    input_data = Column(JSON)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)
    progress_message = Column(String(512), nullable=True)
    celery_task_id = Column(String(256), nullable=True, index=True)
    created_by = Column(String(64), default="system")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    algorithm = relationship("Algorithm", back_populates="tasks")

    __table_args__ = (
        Index("ix_task_status_created", "status", "created_at"),
    )


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id = Column(String(128), primary_key=True)
    algorithm_id = Column(String(128), ForeignKey("algorithms.id"), index=True)
    task_id = Column(String(128), ForeignKey("tasks.id"), nullable=True)
    name = Column(String(128), nullable=False)
    model_type = Column(String(32))
    file_path = Column(String(512))
    metrics = Column(JSON, nullable=True)
    feature_keys = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def migrate_from_filesystem(db: Session, database_dir: str = None):
    from pathlib import Path
    try:
        from api_server import parse_cif_file, DATABASE_DIR as _DB_DIR
    except ImportError:
        _DB_DIR = Path(__file__).parent / "database"
        print(f"⚠️ 无法导入 api_server，使用默认数据库路径: {_DB_DIR}")

    db_dir = Path(database_dir) if database_dir else _DB_DIR

    existing_protos = db.query(Prototype).count()
    existing_mats = db.query(Material).count()

    if existing_protos > 0 and existing_mats > 0:
        return {"skipped": True, "reason": f"DB already has {existing_protos} prototypes, {existing_mats} materials"}

    imported_protos = 0
    imported_mats = 0
    errors = []

    try:
        # 先禁用外键约束检查（MySQL 特定）
        if 'mysql' in DATABASE_URL:
            try:
                db.execute(text('SET FOREIGN_KEY_CHECKS=0'))
                db.commit()
                print("✓ 已禁用外键约束检查")
            except Exception as e:
                print(f"⚠️ 禁用外键约束失败（不影响继续执行）: {e}")
                db.rollback()

        # 先导入所有 Prototype
        print(f"\n开始导入 Prototype (在 {db_dir})...")
        for proto_path in sorted(db_dir.glob("Proto_*.json")):
            proto_id = proto_path.stem.replace("Proto_", "")
            try:
                with open(proto_path, "r", encoding="utf-8") as f:
                    proto_data = json.load(f)

                topo = proto_data.get("topology_theory", {})
                crystal = proto_data.get("prototype_crystallography", {})

                existing = db.query(Prototype).filter_by(id=proto_id).first()
                if existing:
                    continue

                proto = Prototype(
                    id=proto_id,
                    prototype_id=topo.get("prototype_id", ""),
                    expanded_modes=topo.get("expanded_modes", []),
                    reference_grid=topo.get("reference_grid", ""),
                    ideal_space_group=crystal.get("ideal_space_group", ""),
                    space_group_number=crystal.get("space_group_number"),
                    crystal_system=crystal.get("crystal_system", ""),
                    is_neutral=crystal.get("is_neutral"),
                    topology_data=proto_data,
                )
                db.add(proto)
                imported_protos += 1
            except Exception as e:
                errors.append(f"Proto {proto_id}: {str(e)}")

        db.commit()
        print(f"✓ 成功导入 {imported_protos} 个原型")

        # 再导入所有 Material
        print("\n开始导入 Material...")
        for proto_dir in sorted(db_dir.iterdir()):
            if not proto_dir.is_dir():
                continue
            if proto_dir.name.startswith("Raw_Proto_"):
                topology_id = proto_dir.name.replace("Raw_Proto_", "")
                is_verified = False
            elif proto_dir.name.startswith("Verified_Proto_"):
                topology_id = proto_dir.name.replace("Verified_Proto_", "")
                is_verified = True
            else:
                continue

            # 确保该拓扑已存在，不存在则跳过（避免外键问题）
            proto_exists = db.query(Prototype).filter_by(id=topology_id).first()
            if not proto_exists:
                print(f"  ⚠️  拓扑 {topology_id} 不存在，跳过该目录")
                continue

            print(f"\n  处理目录 {proto_dir.name} (拓扑 {topology_id})...")
            for cif_path in sorted(proto_dir.glob("*.cif")):
                material_id = cif_path.stem
                try:
                    existing = db.query(Material).filter_by(id=material_id).first()
                    if existing:
                        continue

                    if 'parse_cif_file' in globals():
                        cif_data = parse_cif_file(cif_path)
                        if not cif_data:
                            continue

                        lattice = cif_data.get("lattice", {})
                        formula = cif_data.get("formula", "")
                        space_group = cif_data.get("space_group", "")
                        atom_sites = cif_data.get("atom_sites", [])
                        elements = list(set(s["element"] for s in atom_sites)) if atom_sites else []
                    else:
                        lattice = {}
                        formula = material_id
                        space_group = "P1"
                        elements = []

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
                        n_atoms=len(elements) if elements else 0,
                        is_verified=is_verified,
                        source="verified" if is_verified else "raw",
                        cif_path=str(cif_path.relative_to(db_dir)),
                    )
                    db.add(mat)
                    imported_mats += 1

                    # 每100个提交一次，避免内存堆积
                    if imported_mats % 100 == 0:
                        db.commit()
                        print(f"    已导入 {imported_mats} 个材料...")
                except Exception as e:
                    errors.append(f"Material {material_id}: {str(e)}")

        db.commit()
        print(f"\n✓ 成功导入 {imported_mats} 个材料")

        return {
            "imported_prototypes": imported_protos,
            "imported_materials": imported_mats,
            "errors": errors[:20],
            "total_errors": len(errors),
        }
    finally:
        # 重新启用外键约束
        if 'mysql' in DATABASE_URL:
            try:
                db.execute(text('SET FOREIGN_KEY_CHECKS=1'))
                db.commit()
                print("✓ 已重新启用外键约束")
            except Exception:
                pass
