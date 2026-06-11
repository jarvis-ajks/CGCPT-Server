import os
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Generator, Any

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index,
    Enum as SAEnum,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_timeout=30,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after use.

    Intended as a FastAPI dependency injection generator.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables that do not yet exist."""
    Base.metadata.create_all(bind=engine)


class Prototype(Base):
    """Crystal structure prototype model.

    Represents a unique topological arrangement of layer modes
    in a perovskite-type crystal structure.
    """

    __tablename__ = "prototypes"

    id: str = Column(String(128), primary_key=True)
    prototype_id: Optional[str] = Column(String(128), index=True)
    expanded_modes: Optional[list] = Column(JSON)
    reference_grid: Optional[str] = Column(String(64))
    ideal_space_group: Optional[str] = Column(String(64))
    space_group_number: Optional[int] = Column(Integer)
    crystal_system: Optional[str] = Column(String(32))
    is_neutral: Optional[bool] = Column(Boolean)
    topology_data: Optional[dict] = Column(JSON)
    created_at: Optional[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    materials = relationship("Material", back_populates="prototype")

    __table_args__ = (Index("ix_proto_crystal_system", "crystal_system"),)

    def __repr__(self) -> str:
        return f"<Prototype(id={self.id!r}, space_group={self.ideal_space_group!r})>"


class Material(Base):
    """Crystal material model.

    Represents a specific material instance with crystallographic
    data and its associated prototype topology.
    """

    __tablename__ = "materials"

    id: str = Column(String(256), primary_key=True)
    formula: Optional[str] = Column(String(128), index=True)
    space_group: Optional[str] = Column(String(64), index=True)
    topology_id: Optional[str] = Column(String(128), ForeignKey("prototypes.id"), index=True)
    elements: Optional[list] = Column(JSON)
    lattice_a: Optional[float] = Column(Float)
    lattice_b: Optional[float] = Column(Float)
    lattice_c: Optional[float] = Column(Float)
    lattice_alpha: Optional[float] = Column(Float)
    lattice_beta: Optional[float] = Column(Float)
    lattice_gamma: Optional[float] = Column(Float)
    n_atoms: Optional[int] = Column(Integer)
    is_verified: bool = Column(Boolean, default=False)
    source: str = Column(String(32), default="raw")
    cif_path: Optional[str] = Column(String(512))
    cif_content: Optional[str] = Column(Text, nullable=True)
    metadata_json: Optional[dict] = Column(JSON, nullable=True)
    created_at: Optional[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    prototype = relationship("Prototype", back_populates="materials")

    __table_args__ = (
        Index("ix_mat_formula_sg", "formula", "space_group"),
        Index("ix_mat_verified", "is_verified"),
    )

    def __repr__(self) -> str:
        return f"<Material(id={self.id!r}, formula={self.formula!r}, space_group={self.space_group!r})>"


class Algorithm(Base):
    """Algorithm model.

    Stores metadata about a prediction or analysis algorithm,
    including its entry point, schemas, and configuration.
    """

    __tablename__ = "algorithms"

    id: str = Column(String(128), primary_key=True)
    name: str = Column(String(128), nullable=False)
    description: Optional[str] = Column(Text)
    version: str = Column(String(32), default="1.0.0")
    algorithm_type: Optional[str] = Column(String(32), index=True)
    entry_point: str = Column(String(256), nullable=False)
    input_schema: Optional[dict] = Column(JSON)
    output_schema: Optional[dict] = Column(JSON)
    config_schema: Optional[dict] = Column(JSON, nullable=True)
    default_config: Optional[dict] = Column(JSON, nullable=True)
    is_active: bool = Column(Boolean, default=True)
    created_at: Optional[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tasks = relationship("Task", back_populates="algorithm")

    def __repr__(self) -> str:
        return f"<Algorithm(id={self.id!r}, name={self.name!r})>"


class Task(Base):
    """Task model.

    Tracks the execution state of an algorithm run, including
    status, progress, input/output data, and timing information.
    """

    __tablename__ = "tasks"

    id: str = Column(String(128), primary_key=True)
    algorithm_id: Optional[str] = Column(String(128), ForeignKey("algorithms.id"), index=True)
    status: str = Column(
        SAEnum("pending", "running", "completed", "failed", "cancelled", name="task_status"),
        default="pending",
        index=True,
    )
    input_data: Optional[dict] = Column(JSON)
    output_data: Optional[dict] = Column(JSON, nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    progress: float = Column(Float, default=0.0)
    progress_message: Optional[str] = Column(String(512), nullable=True)
    celery_task_id: Optional[str] = Column(String(256), nullable=True, index=True)
    created_by: str = Column(String(64), default="system")
    started_at: Optional[datetime] = Column(DateTime, nullable=True)
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)
    created_at: Optional[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    algorithm = relationship("Algorithm", back_populates="tasks")

    __table_args__ = (Index("ix_task_status_created", "status", "created_at"),)

    def __repr__(self) -> str:
        return f"<Task(id={self.id!r}, status={self.status!r})>"


class ModelArtifact(Base):
    """Model artifact model.

    Stores metadata about a trained ML model file, including
    its type, file path, evaluation metrics, and feature keys.
    """

    __tablename__ = "model_artifacts"

    id: str = Column(String(128), primary_key=True)
    algorithm_id: Optional[str] = Column(String(128), ForeignKey("algorithms.id"), index=True)
    task_id: Optional[str] = Column(String(128), ForeignKey("tasks.id"), nullable=True)
    name: str = Column(String(128), nullable=False)
    model_type: Optional[str] = Column(String(32))
    file_path: Optional[str] = Column(String(512))
    metrics: Optional[dict] = Column(JSON, nullable=True)
    feature_keys: Optional[list] = Column(JSON, nullable=True)
    is_active: bool = Column(Boolean, default=True)
    created_at: Optional[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ModelArtifact(id={self.id!r}, name={self.name!r})>"


def migrate_from_filesystem(db: Session, database_dir: Optional[str] = None) -> dict[str, Any]:
    """Migrate prototype and material data from the filesystem into the database.

    Args:
        db: Active SQLAlchemy session.
        database_dir: Optional path to the database directory on disk.
            Defaults to the directory exported by ``api_server`` or a local
            ``database/`` fallback.

    Returns:
        A dict with import statistics including counts of imported prototypes
        and materials, and any errors encountered.
    """
    from pathlib import Path

    _DB_DIR = Path(__file__).parent / "database"
    parse_cif_file = None
    try:
        from api_server import parse_cif_file as _parse_cif

        parse_cif_file = _parse_cif
    except ImportError:
        pass

    db_dir = Path(database_dir) if database_dir else _DB_DIR

    existing_protos = db.query(Prototype).count()
    existing_mats = db.query(Material).count()

    if existing_protos > 0 and existing_mats > 0:
        return {
            "skipped": True,
            "reason": f"DB already has {existing_protos} prototypes, {existing_mats} materials",
        }

    imported_protos = 0
    imported_mats = 0
    errors: list[str] = []

    try:
        # 先禁用外键约束检查（MySQL 特定）
        if "mysql" in DATABASE_URL:
            try:
                db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
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

                    if parse_cif_file is not None:
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
                        atom_sites = []

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
                        n_atoms=len(atom_sites) if atom_sites else 0,
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
        if "mysql" in DATABASE_URL:
            try:
                db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                db.commit()
                print("✓ 已重新启用外键约束")
            except Exception:
                pass
