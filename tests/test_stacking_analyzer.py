"""Tests for stacking_analyzer module functions."""

import pytest
from unittest.mock import patch, MagicMock

import stacking_analyzer as sa


# ---------------------------------------------------------------------------
# parse_cif_text
# ---------------------------------------------------------------------------

class TestParseCifText:
    def test_parse_cif_text_no_pymatgen(self):
        """When pymatgen is not available, parse_cif_text returns None."""
        with patch.object(sa, "_ensure_pymatgen", return_value={}):
            result = sa.parse_cif_text("some cif text")
            assert result is None

    def test_parse_cif_text_with_mock_pymatgen(self):
        """Test CIF parsing with a mocked pymatgen."""
        mock_site = MagicMock()
        mock_site.specie.symbol = "Ba"
        mock_site.frac_coords = [0.0, 0.0, 0.0]

        mock_lattice = MagicMock()
        mock_lattice.a = 4.0
        mock_lattice.b = 4.0
        mock_lattice.c = 4.0
        mock_lattice.alpha = 90.0
        mock_lattice.beta = 90.0
        mock_lattice.gamma = 90.0

        mock_struct = MagicMock()
        mock_struct.__iter__ = MagicMock(return_value=iter([mock_site]))
        mock_struct.lattice = mock_lattice
        mock_struct.composition.reduced_formula = "Ba"

        mock_parser = MagicMock()
        mock_parser.parse_structures.return_value = [mock_struct]

        pmg = {"CifParser": MagicMock(return_value=mock_parser)}
        with patch.object(sa, "_ensure_pymatgen", return_value=pmg):
            result = sa.parse_cif_text("data_test\n_cell_length_a 4.0")
            assert result is not None
            assert "lattice" in result
            assert "atom_sites" in result
            assert result["lattice"]["a"] == 4.0

    def test_parse_cif_text_empty_structures(self):
        """When CifParser returns empty structures, result is None."""
        mock_parser = MagicMock()
        mock_parser.parse_structures.return_value = []

        pmg = {"CifParser": MagicMock(return_value=mock_parser)}
        with patch.object(sa, "_ensure_pymatgen", return_value=pmg):
            result = sa.parse_cif_text("bad cif")
            assert result is None


# ---------------------------------------------------------------------------
# extract_features
# ---------------------------------------------------------------------------

class TestExtractFeatures:
    def test_extract_features_none_input(self):
        assert sa.extract_features(None) is None

    def test_extract_features_empty_atom_sites(self):
        result = sa.extract_features({"lattice": {}, "atom_sites": []})
        assert result is None

    def test_extract_features_with_mock_data(self, mock_cif_data):
        """Test feature extraction with a realistic mock CIF data dict."""
        # Mock _ensure_pymatgen to return empty so it doesn't try to get Element radii
        with patch.object(sa, "_ensure_pymatgen", return_value={}):
            features = sa.extract_features(mock_cif_data)
            assert features is not None
            assert "n_z_layers" in features
            assert "z_spacing_mean" in features
            assert "layer_type_seq" in features
            assert isinstance(features["n_z_layers"], int)

    def test_extract_features_layer_counts(self, mock_cif_data):
        """Verify layer type counts are present."""
        with patch.object(sa, "_ensure_pymatgen", return_value={}):
            features = sa.extract_features(mock_cif_data)
            assert "n_xo3_layers" in features
            assert "n_m7_layers" in features
            assert "n_main_layers" in features


# ---------------------------------------------------------------------------
# infer_grid
# ---------------------------------------------------------------------------

class TestInferGrid:
    def test_infer_grid_simple(self):
        """Test grid inference with simple integer fractional coords."""
        sites = [(0.0, 0.0), (0.5, 0.5), (0.5, 0.0), (0.0, 0.5)]
        gx, gy = sa.infer_grid(sites)
        assert gx >= 1
        assert gy >= 1

    def test_infer_grid_empty(self):
        """Empty sites should return grid of 1."""
        gx, gy = sa.infer_grid([])
        assert gx == 1
        assert gy == 1

    def test_infer_grid_single(self):
        """Single site should return grid of 1."""
        gx, gy = sa.infer_grid([(0.0, 0.0)])
        assert gx == 1
        assert gy == 1


# ---------------------------------------------------------------------------
# _group_atoms_by_axis
# ---------------------------------------------------------------------------

class TestGroupAtomsByAxis:
    def test_group_atoms_by_axis_basic(self):
        """Test grouping atoms by z coordinate."""
        atoms = [
            {"element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0},
            {"element": "Ti", "x": 0.5, "y": 0.5, "z": 0.5},
            {"element": "O", "x": 0.5, "y": 0.5, "z": 0.0},
        ]
        groups = sa._group_atoms_by_axis(atoms, axis="z", tol=0.02)
        assert len(groups) >= 1
        # Each group is (center, [atoms])
        for center, group_atoms in groups:
            assert isinstance(center, float)
            assert isinstance(group_atoms, list)

    def test_group_atoms_by_axis_empty(self):
        """Empty input should return empty list."""
        result = sa._group_atoms_by_axis([], axis="z")
        assert result == []

    def test_group_atoms_by_axis_single_layer(self):
        """All atoms at same z should form one group."""
        atoms = [
            {"element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0},
            {"element": "Ti", "x": 0.5, "y": 0.5, "z": 0.01},
        ]
        groups = sa._group_atoms_by_axis(atoms, axis="z", tol=0.02)
        assert len(groups) == 1


# ---------------------------------------------------------------------------
# Layer type classification
# ---------------------------------------------------------------------------

class TestLayerTypeClassification:
    def test_layer_type_constants(self):
        """Verify layer type constants are properly defined."""
        assert "XO3" in sa.LAYER_TYPES
        assert "M7" in sa.LAYER_TYPES
        assert "T" in sa.LAYER_TYPES
        assert "XO3" in sa.MAIN_LAYER_TYPES
        assert "M7" in sa.M_LAYER_TYPES

    def test_extract_layer_features_with_mock_data(self, mock_cif_data):
        """Test layer feature extraction and type detection."""
        with patch.object(sa, "_ensure_pymatgen", return_value={}):
            layer_features = sa.extract_layer_features(mock_cif_data)
            assert layer_features is not None
            assert isinstance(layer_features, list)
            for lf in layer_features:
                assert "predicted_type" in lf
                assert "n_atoms" in lf
                assert "has_oxygen" in lf
                assert "z" in lf

    def test_extract_layer_features_none_input(self):
        assert sa.extract_layer_features(None) is None

    def test_extract_layer_features_empty_atoms(self):
        result = sa.extract_layer_features({"lattice": {}, "atom_sites": []})
        assert result is None


# ---------------------------------------------------------------------------
# _choose_layer_axis_and_tol
# ---------------------------------------------------------------------------

class TestChooseLayerAxisAndTol:
    def test_default_axis(self):
        """With empty data, should default to z axis."""
        axis, tol = sa._choose_layer_axis_and_tol({"lattice": {}, "atom_sites": []})
        assert axis == "z"

    def test_with_cubic_lattice(self, mock_cif_data):
        """With cubic lattice data, should return a valid axis."""
        axis, tol = sa._choose_layer_axis_and_tol(mock_cif_data)
        assert axis in ("x", "y", "z")
        assert tol > 0
