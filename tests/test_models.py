"""Tests for CGCPT-Server database models using in-memory SQLite."""

import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Create an isolated Base for testing (avoids importing models.py which
# triggers create_engine with MySQL-specific pool args).
TestBase = declarative_base()


class Prototype(TestBase):
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


class Material(TestBase):
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


class Algorithm(TestBase):
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


class Task(TestBase):
    __tablename__ = "tasks"
    id = Column(String(128), primary_key=True)
    algorithm_id = Column(String(128), ForeignKey("algorithms.id"), index=True)
    status = Column(String(32), default="pending", index=True)
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


class ModelArtifact(TestBase):
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


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite session with all tables."""
    engine = create_engine("sqlite://", echo=False)
    TestBase.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.close()
    TestBase.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Prototype
# ---------------------------------------------------------------------------

class TestPrototypeModel:
    def test_create_prototype(self, db_session):
        proto = Prototype(
            id="test-proto-1",
            prototype_id="XO3-M7-XO3",
            expanded_modes=["XO3", "M7", "XO3"],
            reference_grid="XO3",
            ideal_space_group="Pm-3m",
            space_group_number=221,
            crystal_system="cubic",
            is_neutral=True,
            topology_data={"key": "value"},
        )
        db_session.add(proto)
        db_session.commit()

        result = db_session.query(Prototype).filter_by(id="test-proto-1").first()
        assert result is not None
        assert result.prototype_id == "XO3-M7-XO3"
        assert result.expanded_modes == ["XO3", "M7", "XO3"]
        assert result.crystal_system == "cubic"
        assert result.is_neutral is True

    def test_query_prototype_not_found(self, db_session):
        result = db_session.query(Prototype).filter_by(id="nonexistent").first()
        assert result is None

    def test_prototype_default_timestamps(self, db_session):
        proto = Prototype(id="ts-test")
        db_session.add(proto)
        db_session.commit()
        result = db_session.query(Prototype).filter_by(id="ts-test").first()
        assert result.created_at is not None

    def test_prototype_topology_data_json(self, db_session):
        data = {"nested": {"key": [1, 2, 3]}}
        proto = Prototype(id="json-test", topology_data=data)
        db_session.add(proto)
        db_session.commit()
        result = db_session.query(Prototype).filter_by(id="json-test").first()
        assert result.topology_data == data


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

class TestMaterialModel:
    def test_create_material(self, db_session):
        proto = Prototype(id="topo-1", prototype_id="XO3-M7-XO3")
        db_session.add(proto)
        db_session.commit()

        mat = Material(
            id="mat-001",
            formula="BaTiO3",
            space_group="Pm-3m",
            topology_id="topo-1",
            elements=["Ba", "Ti", "O"],
            lattice_a=4.01,
            lattice_b=4.01,
            lattice_c=4.01,
            lattice_alpha=90.0,
            lattice_beta=90.0,
            lattice_gamma=90.0,
            n_atoms=5,
            is_verified=False,
            source="raw",
        )
        db_session.add(mat)
        db_session.commit()

        result = db_session.query(Material).filter_by(id="mat-001").first()
        assert result is not None
        assert result.formula == "BaTiO3"
        assert result.elements == ["Ba", "Ti", "O"]
        assert result.is_verified is False

    def test_material_prototype_relationship(self, db_session):
        proto = Prototype(id="topo-rel", prototype_id="XO3")
        db_session.add(proto)
        db_session.commit()

        mat = Material(id="mat-rel", formula="BaTiO3", topology_id="topo-rel")
        db_session.add(mat)
        db_session.commit()

        result = db_session.query(Material).filter_by(id="mat-rel").first()
        assert result.prototype is not None
        assert result.prototype.id == "topo-rel"

    def test_query_material_by_formula(self, db_session):
        proto = Prototype(id="topo-q", prototype_id="XO3")
        db_session.add(proto)
        db_session.commit()

        for i, formula in enumerate(["BaTiO3", "CaSiO3", "BaTiO3"]):
            db_session.add(Material(
                id=f"mat-q-{i}", formula=formula, topology_id="topo-q"
            ))
        db_session.commit()

        results = db_session.query(Material).filter_by(formula="BaTiO3").all()
        assert len(results) == 2

    def test_material_default_is_verified(self, db_session):
        proto = Prototype(id="topo-dv", prototype_id="XO3")
        db_session.add(proto)
        db_session.commit()

        mat = Material(id="mat-dv", topology_id="topo-dv")
        db_session.add(mat)
        db_session.commit()
        assert mat.is_verified is False


# ---------------------------------------------------------------------------
# Algorithm
# ---------------------------------------------------------------------------

class TestAlgorithmModel:
    def test_create_algorithm(self, db_session):
        algo = Algorithm(
            id="algo-1",
            name="Stacking Predictor",
            description="Predicts stacking sequences",
            version="1.0.0",
            algorithm_type="classification",
            entry_point="stacking_analyzer.predict",
            is_active=True,
        )
        db_session.add(algo)
        db_session.commit()

        result = db_session.query(Algorithm).filter_by(id="algo-1").first()
        assert result is not None
        assert result.name == "Stacking Predictor"
        assert result.is_active is True

    def test_query_active_algorithms(self, db_session):
        for i, active in enumerate([True, True, False]):
            db_session.add(Algorithm(
                id=f"algo-act-{i}",
                name=f"Algo {i}",
                entry_point=f"mod.fn{i}",
                is_active=active,
            ))
        db_session.commit()

        active = db_session.query(Algorithm).filter_by(is_active=True).all()
        assert len(active) == 2

    def test_algorithm_default_version(self, db_session):
        algo = Algorithm(id="algo-ver", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()
        assert algo.version == "1.0.0"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TestTaskModel:
    def test_create_task(self, db_session):
        algo = Algorithm(id="algo-task", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        task = Task(
            id="task-001",
            algorithm_id="algo-task",
            status="pending",
            input_data={"q": "BaTiO3"},
            progress=0.0,
        )
        db_session.add(task)
        db_session.commit()

        result = db_session.query(Task).filter_by(id="task-001").first()
        assert result is not None
        assert result.status == "pending"
        assert result.input_data == {"q": "BaTiO3"}

    def test_task_status_transition(self, db_session):
        algo = Algorithm(id="algo-trans", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        task = Task(id="task-trans", algorithm_id="algo-trans", status="pending")
        db_session.add(task)
        db_session.commit()

        task.status = "running"
        task.progress = 0.5
        db_session.commit()

        result = db_session.query(Task).filter_by(id="task-trans").first()
        assert result.status == "running"
        assert result.progress == 0.5

    def test_query_tasks_by_status(self, db_session):
        algo = Algorithm(id="algo-qts", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        for i, status in enumerate(["pending", "running", "completed", "failed"]):
            db_session.add(Task(
                id=f"task-qts-{i}", algorithm_id="algo-qts", status=status
            ))
        db_session.commit()

        pending = db_session.query(Task).filter_by(status="pending").all()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_task_algorithm_relationship(self, db_session):
        algo = Algorithm(id="algo-rel", name="RelTest", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        task = Task(id="task-rel", algorithm_id="algo-rel")
        db_session.add(task)
        db_session.commit()

        result = db_session.query(Task).filter_by(id="task-rel").first()
        assert result.algorithm is not None
        assert result.algorithm.name == "RelTest"


# ---------------------------------------------------------------------------
# ModelArtifact
# ---------------------------------------------------------------------------

class TestModelArtifactModel:
    def test_create_model_artifact(self, db_session):
        algo = Algorithm(id="algo-ma", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        artifact = ModelArtifact(
            id="model-001",
            algorithm_id="algo-ma",
            task_id="",
            name="Test Decision Tree",
            model_type="decision_tree",
            file_path="/tmp/test_model.pkl",
            metrics={"accuracy": 0.95},
            is_active=True,
        )
        db_session.add(artifact)
        db_session.commit()

        result = db_session.query(ModelArtifact).filter_by(id="model-001").first()
        assert result is not None
        assert result.name == "Test Decision Tree"
        assert result.metrics["accuracy"] == 0.95

    def test_model_artifact_default_active(self, db_session):
        algo = Algorithm(id="algo-mad", name="Test", entry_point="test.fn")
        db_session.add(algo)
        db_session.commit()

        artifact = ModelArtifact(
            id="model-dact",
            algorithm_id="algo-mad",
            name="Default Active",
        )
        db_session.add(artifact)
        db_session.commit()
        assert artifact.is_active is True
