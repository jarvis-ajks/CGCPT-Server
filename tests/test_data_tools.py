"""Tests for data_tools module."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestExportMaterialsJsonFormat:
    def test_export_materials_creates_json(self):
        """Test that export_materials writes a valid JSON file."""
        mock_material = MagicMock()
        mock_material.id = "mat-001"
        mock_material.formula = "BaTiO3"
        mock_material.space_group = "Pm-3m"
        mock_material.topology_id = "topo-1"
        mock_material.elements = ["Ba", "Ti", "O"]
        mock_material.lattice_a = 4.01
        mock_material.lattice_b = 4.01
        mock_material.lattice_c = 4.01
        mock_material.lattice_alpha = 90.0
        mock_material.lattice_beta = 90.0
        mock_material.lattice_gamma = 90.0
        mock_material.n_atoms = 5
        mock_material.is_verified = False
        mock_material.source = "raw"
        mock_material.cif_path = "/data/BaTiO3.cif"
        mock_material.cif_content = None
        mock_material.metadata_json = None
        mock_material.created_at = None
        mock_material.updated_at = None

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_material]
        mock_session.close = MagicMock()

        mock_session_local = MagicMock(return_value=mock_session)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "materials_test.json"
            # data_tools imports SessionLocal from models inside the function
            with patch("models.SessionLocal", mock_session_local):
                import data_tools
                result = data_tools.export_materials(output_file)
                assert result == output_file
                assert output_file.exists()

                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert "materials" in data
                assert "count" in data
                assert data["count"] == 1
                assert data["materials"][0]["id"] == "mat-001"
                assert data["materials"][0]["formula"] == "BaTiO3"


class TestExportPrototypesJsonFormat:
    def test_export_prototypes_creates_json(self):
        """Test that export_prototypes writes a valid JSON file."""
        mock_proto = MagicMock()
        mock_proto.id = "topo-1"
        mock_proto.prototype_id = "XO3-M7-XO3"
        mock_proto.expanded_modes = ["XO3", "M7", "XO3"]
        mock_proto.reference_grid = "XO3"
        mock_proto.ideal_space_group = "Pm-3m"
        mock_proto.space_group_number = 221
        mock_proto.crystal_system = "cubic"
        mock_proto.is_neutral = True
        mock_proto.topology_data = {"key": "value"}
        mock_proto.created_at = None
        mock_proto.updated_at = None

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_proto]
        mock_session.close = MagicMock()

        mock_session_local = MagicMock(return_value=mock_session)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "prototypes_test.json"
            with patch("models.SessionLocal", mock_session_local):
                import data_tools
                result = data_tools.export_prototypes(output_file)
                assert result == output_file
                assert output_file.exists()

                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert "prototypes" in data
                assert "count" in data
                assert data["count"] == 1
                assert data["prototypes"][0]["id"] == "topo-1"
                assert data["prototypes"][0]["crystal_system"] == "cubic"
