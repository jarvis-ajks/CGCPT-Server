"""Pytest fixtures for CGCPT-Server test suite."""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Mock heavy / unavailable modules BEFORE importing application code
# ---------------------------------------------------------------------------
# pymatgen, sklearn, joblib, psutil etc. may not be installed in CI.
# We create lightweight stubs so that import-time failures are avoided.
_STUB_MODULES = [
    "pymatgen",
    "pymatgen.core",
    "pymatgen.io",
    "pymatgen.io.cif",
    "pymatgen.symmetry",
    "pymatgen.symmetry.analyzer",
    "pymatgen.analysis",
    "pymatgen.analysis.structure_matcher",
    "sklearn",
    "sklearn.tree",
    "sklearn.ensemble",
    "sklearn.neighbors",
    "sklearn.model_selection",
    "sklearn.metrics",
    "sklearn.preprocessing",
    "joblib",
    "psutil",
]

for mod_name in _STUB_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Make psutil.virtual_memory() return a JSON-serializable mock
_psutil_mock = sys.modules.get("psutil")
if _psutil_mock is not None:
    _mem_mock = MagicMock()
    _mem_mock.total = 16 * 1024 * 1024 * 1024  # 16 GB
    _mem_mock.used = 8 * 1024 * 1024 * 1024   # 8 GB
    _mem_mock.percent = 50.0
    _psutil_mock.virtual_memory = MagicMock(return_value=_mem_mock)

# Patch DATABASE_URL before importing config/models so they don't try MySQL.
# Use a plain sqlite URL (no pool args) so models.py create_engine works.
os.environ["CGCPT_DB_URL"] = "sqlite:///test_cgcpt.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASS", "testpass")


@pytest.fixture(scope="session")
def app():
    """Create a Flask application instance for testing."""
    # Patch DATABASE_DIR to a temp dir so build_indexes doesn't scan the real DB
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal prototype JSON so list_prototypes returns something
        proto_dir = Path(tmpdir)
        proto_json = proto_dir / "Proto_TestTopo.json"
        proto_json.write_text(
            '{"topology_theory":{"prototype_id":"test","expanded_modes":["XO3","M7","XO3"],'
            '"reference_grid":"XO3"},"prototype_crystallography":{'
            '"ideal_space_group":"Pm-3m","space_group_number":221,'
            '"crystal_system":"cubic","is_neutral":true},"real_compounds":[]}',
            encoding="utf-8",
        )

        # Create a CIF directory with one sample CIF
        cif_dir = proto_dir / "Raw_Proto_TestTopo"
        cif_dir.mkdir()
        cif_file = cif_dir / "BaTiO3_Pm-3m_mp-2998.cif"
        cif_file.write_text(
            "data_BaTiO3\n"
            "_cell_length_a 4.01\n"
            "_cell_length_b 4.01\n"
            "_cell_length_c 4.01\n"
            "_cell_angle_alpha 90\n"
            "_cell_angle_beta 90\n"
            "_cell_angle_gamma 90\n"
            "_symmetry_space_group_name_H-M 'Pm-3m'\n"
            "_chemical_formula_structural BaTiO3\n"
            "loop_\n"
            "_atom_site_label\n"
            "_atom_site_type_symbol\n"
            "_atom_site_fract_x\n"
            "_atom_site_fract_y\n"
            "_atom_site_fract_z\n"
            "Ba1 Ba 0.0 0.0 0.0\n"
            "Ti1 Ti 0.5 0.5 0.5\n"
            "O1 O 0.5 0.5 0.0\n"
            "O2 O 0.5 0.0 0.5\n"
            "O3 O 0.0 0.5 0.5\n",
            encoding="utf-8",
        )

        with patch("api_server.DATABASE_DIR", proto_dir), \
             patch("api_server.CFG_DATABASE_DIR", str(proto_dir)):
            # Reset module-level indexes so they rebuild with our test dir
            from collections import defaultdict
            import api_server
            api_server._indexes_built = False
            api_server.prototypes_index = {}
            api_server.materials_index = {}
            api_server.topology_to_materials = defaultdict(list)
            api_server.element_to_materials = defaultdict(set)
            api_server.space_group_to_materials = defaultdict(list)
            api_server.formula_to_materials = defaultdict(list)
            api_server.all_elements = set()
            api_server._api_cache = {}
            api_server._api_cache_ttl = {}

            app = api_server.app
            app.config["TESTING"] = True
            yield app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def mock_cif_data():
    """Sample CIF data dict with lattice and atom_sites."""
    return {
        "lattice": {
            "a": 4.01,
            "b": 4.01,
            "c": 4.01,
            "alpha": 90.0,
            "beta": 90.0,
            "gamma": 90.0,
        },
        "atom_sites": [
            {"element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0},
            {"element": "Ti", "x": 0.5, "y": 0.5, "z": 0.5},
            {"element": "O", "x": 0.5, "y": 0.5, "z": 0.0},
            {"element": "O", "x": 0.5, "y": 0.0, "z": 0.5},
            {"element": "O", "x": 0.0, "y": 0.5, "z": 0.5},
        ],
        "formula": "BaTiO3",
        "space_group": "Pm-3m",
    }


@pytest.fixture()
def mock_db():
    """In-memory SQLite database session for model tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite://", echo=False)
    import models
    # Re-bind the Base metadata to the in-memory engine
    models.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = TestSession()
    yield session

    session.close()
    models.Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def auth_token():
    """Return a valid base64 auth token for the test admin user."""
    import base64
    return base64.b64encode(b"admin:testpass").decode()
