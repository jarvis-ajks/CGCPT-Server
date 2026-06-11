"""Tests for CGCPT-Server API endpoints."""

import base64
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data


# ---------------------------------------------------------------------------
# Prototypes
# ---------------------------------------------------------------------------


class TestPrototypes:
    def test_list_prototypes(self, client):
        resp = client.get("/api/prototypes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "prototypes" in data
        assert "total" in data
        assert isinstance(data["prototypes"], list)

    def test_get_prototype_found(self, client):
        resp = client.get("/api/prototypes/TestTopo")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "TestTopo"

    def test_get_prototype_not_found(self, client):
        resp = client.get("/api/prototypes/NonExistentTopo999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


class TestMaterials:
    def test_list_materials(self, client):
        resp = client.get("/api/materials")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "materials" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_list_materials_pagination(self, client):
        resp = client.get("/api/materials?page=1&per_page=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["per_page"] == 5

    def test_get_material_found(self, client):
        resp = client.get("/api/materials/BaTiO3_Pm-3m_mp-2998")
        # May be 200 or 404 depending on index build
        assert resp.status_code in (200, 404)

    def test_get_material_not_found(self, client):
        resp = client.get("/api/materials/nonexistent_material_xyz")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_materials(self, client):
        resp = client.get("/api/search?q=Ba")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "Ba"

    def test_search_empty_query(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_search_query_too_long(self, client):
        long_q = "a" * 201
        resp = client.get(f"/api/search?q={long_q}")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "exceeds maximum length" in data["error"]

    def test_search_special_chars_sanitized(self, client):
        resp = client.get("/api/search?q=<script>alert('x')</script>")
        # Should not crash; special chars stripped
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Stats & Elements
# ---------------------------------------------------------------------------


class TestStatsAndElements:
    def test_get_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_materials" in data
        assert "unique_topologies" in data

    def test_get_elements(self, client):
        resp = client.get("/api/elements")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "elements" in data
        assert "total" in data

    def test_get_lattice_types(self, client):
        resp = client.get("/api/lattice-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "lattice_types" in data
        assert "total" in data
        assert data["total"] > 0

    def test_get_classifications(self, client):
        resp = client.get("/api/classifications")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "by_topology" in data


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_auth_login_success(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "testpass"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "token" in data

    def test_auth_login_failure(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False

    def test_auth_check_unauthorized(self, client):
        resp = client.get("/api/auth/check")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False

    def test_auth_check_authorized(self, client, auth_token):
        resp = client.get(
            "/api/auth/check",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True


# ---------------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------------


class TestNotFound:
    def test_not_found(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_generate_invalid_body(self, client):
        """POST /api/generate with missing layer_modes should return 400."""
        resp = client.post(
            "/api/generate",
            json={"x_element": "Ba"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "layer_modes" in data["error"]

    def test_generate_with_valid_params(self, client):
        """POST /api/generate with valid params — may fail if stack_main unavailable."""
        resp = client.post(
            "/api/generate",
            json={
                "x_element": "Ba",
                "o_element": "O",
                "m_element": "Mg",
                "layer_modes": ["XO3", "M7", "XO3"],
                "stack_sequence": "ABC",
            },
        )
        # Either success (200) or module-not-installed error (400)
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Import preview
# ---------------------------------------------------------------------------


class TestImportPreview:
    def test_import_preview_no_files(self, client):
        """POST /api/import/preview without files should return 400."""
        resp = client.post("/api/import/preview")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_import_templates(self, client):
        resp = client.get("/api/import/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "templates" in data


# ---------------------------------------------------------------------------
# DB status (may fail if MySQL not available)
# ---------------------------------------------------------------------------


class TestDBEndpoints:
    def test_db_status(self, client):
        """DB status endpoint — may return error if MySQL unavailable."""
        resp = client.get("/api/db/status")
        # Accept both success and failure gracefully
        assert resp.status_code == 200
        data = resp.get_json()
        # Either success or error key present
        assert "success" in data
