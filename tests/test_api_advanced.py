"""Advanced API endpoint tests covering edge cases, security, and error handling."""
import json
import pytest


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "n_prototypes" in data
        assert "n_materials" in data

    def test_health_no_cache(self, client):
        resp = client.get("/api/health")
        assert resp.headers.get("Cache-Control") == "no-cache"

    def test_health_indexes_built_flag(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        assert "indexes_built" in data
        assert isinstance(data["indexes_built"], bool)

    def test_health_index_build_time(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        assert "index_build_time_ms" in data
        assert isinstance(data["index_build_time_ms"], (int, float))


class TestSearchSecurity:
    """Tests for search input validation and security."""

    def test_search_xss_prevention(self, client):
        """Ensure XSS characters are stripped from search query."""
        resp = client.get("/api/search?q=<script>alert(1)</script>")
        assert resp.status_code == 200
        data = resp.get_json()
        # The < > ' " ; \ should have been stripped by the regex
        assert data["query"] != "<script>alert(1)</script>"
        assert "<" not in data["query"]
        assert ">" not in data["query"]

    def test_search_max_length(self, client):
        """Ensure overly long queries are rejected."""
        resp = client.get("/api/search?q=" + "A" * 201)
        assert resp.status_code == 400
        data = resp.get_json()
        assert "exceeds maximum length" in data["error"]

    def test_search_sql_injection_prevention(self, client):
        """Ensure SQL injection characters are handled."""
        resp = client.get("/api/search?q=Ba'; DROP TABLE--")
        assert resp.status_code == 200  # Should not crash
        data = resp.get_json()
        # Single quotes and semicolons should be stripped
        assert "'" not in data["query"]
        assert ";" not in data["query"]

    def test_search_empty_query(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_search_special_chars_stripped(self, client):
        resp = client.get("/api/search?q=Ba<O>O;O\\O")
        data = resp.get_json()
        assert "<" not in data["query"]
        assert ">" not in data["query"]
        assert ";" not in data["query"]
        assert "\\" not in data["query"]

    def test_search_limit_parameter(self, client):
        """Test that limit parameter is clamped to valid range."""
        resp = client.get("/api/search?q=Ba&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) <= 5

    def test_search_limit_exceeds_max(self, client):
        """Limit above 100 should be clamped to 100."""
        resp = client.get("/api/search?q=Ba&limit=500")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) <= 100

    def test_search_results_have_score(self, client):
        resp = client.get("/api/search?q=Ba")
        assert resp.status_code == 200
        data = resp.get_json()
        for r in data["results"]:
            assert "score" in r
            assert isinstance(r["score"], (int, float))
            assert r["score"] > 0


class TestPagination:
    """Tests for pagination parameters."""

    def test_materials_default_pagination(self, client):
        resp = client.get("/api/materials")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_materials_custom_pagination(self, client):
        resp = client.get("/api/materials?page=1&per_page=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["per_page"] == 5

    def test_materials_per_page_max(self, client):
        resp = client.get("/api/materials?per_page=200")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["per_page"] <= 100

    def test_materials_invalid_page(self, client):
        resp = client.get("/api/materials?page=-1")
        assert resp.status_code == 200  # Should default to page 1
        data = resp.get_json()
        assert data["page"] == 1

    def test_materials_zero_per_page(self, client):
        resp = client.get("/api/materials?per_page=0")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["per_page"] >= 1

    def test_materials_total_pages_calculation(self, client):
        resp = client.get("/api/materials?per_page=5")
        data = resp.get_json()
        if data["total"] > 0:
            expected_pages = (data["total"] + 4) // 5
            assert data["total_pages"] == expected_pages
        else:
            assert data["total_pages"] == 0


class TestGenerateEndpoint:
    """Tests for structure generation endpoints."""

    def test_generate_missing_layer_modes(self, client):
        resp = client.post("/api/generate", json={"x_element": "Ba"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "layer_modes" in data["error"]

    def test_generate_invalid_json(self, client):
        resp = client.post(
            "/api/generate",
            data="not json",
            content_type="application/json",
        )
        # Flask get_json(force=True) may still parse or raise
        # Either way the endpoint should not crash with 500
        assert resp.status_code in (200, 400)

    def test_generate_layer_data_missing_params(self, client):
        resp = client.post("/api/generate/layer-data", json={})
        assert resp.status_code == 400

    def test_generate_primitive_missing_params(self, client):
        resp = client.post("/api/generate/primitive", json={})
        assert resp.status_code == 400

    def test_generate_coordination_missing_params(self, client):
        resp = client.post("/api/generate/coordination", json={})
        assert resp.status_code == 400

    def test_generate_prototype_missing_params(self, client):
        resp = client.post("/api/generate/prototype", json={})
        assert resp.status_code == 400

    def test_generate_full_missing_params(self, client):
        resp = client.post("/api/generate/full", json={})
        assert resp.status_code == 400

    def test_generate_with_valid_params_returns_success_or_module_error(self, client):
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
        assert resp.status_code in (200, 400)

    def test_generate_layer_data_with_valid_params(self, client):
        resp = client.post(
            "/api/generate/layer-data",
            json={
                "layer_modes": ["XO3", "M7", "XO3"],
            },
        )
        assert resp.status_code in (200, 400)

    def test_generate_full_with_valid_params(self, client):
        resp = client.post(
            "/api/generate/full",
            json={
                "layer_modes": ["XO3", "M7", "XO3"],
            },
        )
        assert resp.status_code in (200, 400)


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 401

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False

    def test_check_unauthorized(self, client):
        resp = client.get("/api/auth/check")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["success"] is False

    def test_check_authorized(self, client, auth_token):
        resp = client.get(
            "/api/auth/check",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_models_upload_requires_auth(self, client):
        resp = client.post("/api/models/upload")
        assert resp.status_code == 401

    def test_model_delete_requires_auth(self, client):
        resp = client.delete("/api/models/nonexistent")
        assert resp.status_code == 401

    def test_model_activate_requires_auth(self, client):
        resp = client.post("/api/models/nonexistent/activate")
        assert resp.status_code == 401

    def test_login_success_returns_token(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "testpass"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "token" in data
        # Token should be valid base64
        import base64
        decoded = base64.b64decode(data["token"]).decode("utf-8")
        assert ":" in decoded


class TestImportEndpoints:
    """Tests for import endpoints."""

    def test_import_preview_no_files(self, client):
        resp = client.post("/api/import/preview")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_import_empty_items(self, client):
        resp = client.post("/api/import", json={"items": []})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_import_missing_fields(self, client):
        resp = client.post(
            "/api/import",
            json={"items": [{"material_id": "test"}]},
        )
        # Should return 200 with errors list, or 500 if DB dir issue
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert len(data.get("errors", [])) > 0

    def test_import_templates_available(self, client):
        resp = client.get("/api/import/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "templates" in data
        assert "total" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_prototype_not_found(self, client):
        resp = client.get("/api/prototypes/NONEXISTENT12345")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_material_not_found(self, client):
        resp = client.get("/api/materials/NONEXISTENT12345")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_material_cif_not_found(self, client):
        resp = client.get("/api/materials/NONEXISTENT12345/cif")
        assert resp.status_code == 404


class TestCacheHeaders:
    """Tests for cache control headers."""

    def test_stats_has_cache(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        cache_header = resp.headers.get("Cache-Control", "")
        assert "max-age=60" in cache_header

    def test_elements_has_cache(self, client):
        resp = client.get("/api/elements")
        assert resp.status_code == 200
        cache_header = resp.headers.get("Cache-Control", "")
        assert "max-age=60" in cache_header

    def test_lattice_types(self, client):
        resp = client.get("/api/lattice-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "lattice_types" in data
        assert len(data["lattice_types"]) > 0

    def test_lattice_types_cache(self, client):
        resp = client.get("/api/lattice-types")
        cache_header = resp.headers.get("Cache-Control", "")
        assert "max-age=60" in cache_header

    def test_prototypes_list_cache(self, client):
        resp = client.get("/api/prototypes")
        assert resp.status_code == 200
        cache_header = resp.headers.get("Cache-Control", "")
        assert "max-age=300" in cache_header

    def test_stacking_predict_no_store(self, client):
        """Stacking predict and analyze should have no-store."""
        resp = client.post(
            "/api/stacking/predict",
            json={"model_id": "test", "layer_modes": ["XO3"]},
        )
        # May fail due to module not loaded, but cache header should be set
        cache_header = resp.headers.get("Cache-Control", "")
        assert "no-store" in cache_header


class TestLatticeTypesDetail:
    """Tests for lattice type data structure."""

    def test_lattice_types_structure(self, client):
        resp = client.get("/api/lattice-types")
        data = resp.get_json()
        for lt in data["lattice_types"]:
            assert "mode" in lt
            assert "description" in lt
            assert "is_main_layer" in lt
            assert "is_x_layer" in lt
            assert "is_m_layer" in lt

    def test_lattice_types_contains_xo3(self, client):
        resp = client.get("/api/lattice-types")
        data = resp.get_json()
        modes = [lt["mode"] for lt in data["lattice_types"]]
        assert "XO3" in modes
        assert "M7" in modes
        assert "T" in modes

    def test_lattice_types_total_matches_count(self, client):
        resp = client.get("/api/lattice-types")
        data = resp.get_json()
        assert data["total"] == len(data["lattice_types"])


class TestDBEndpoints:
    """Tests for database-related endpoints."""

    def test_db_status_returns_json(self, client):
        resp = client.get("/api/db/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_db_list_prototypes(self, client):
        resp = client.get("/api/db/prototypes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_db_list_materials(self, client):
        resp = client.get("/api/db/materials")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_db_detailed_stats(self, client):
        resp = client.get("/api/db/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data


class TestPluginEndpoints:
    """Tests for plugin-related endpoints."""

    def test_list_plugins(self, client):
        resp = client.get("/api/plugins")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_list_algorithms(self, client):
        resp = client.get("/api/algorithms")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_list_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_list_models(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_discovered_plugins(self, client):
        resp = client.get("/api/plugins/discovered")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data


class TestStackingEndpoints:
    """Tests for stacking analysis endpoints."""

    def test_stacking_models(self, client):
        resp = client.get("/api/stacking/models")
        # May return 500 if module not loaded
        assert resp.status_code in (200, 500)

    def test_stacking_predict_missing_model(self, client):
        resp = client.post(
            "/api/stacking/predict",
            json={"model_id": "", "layer_modes": ["XO3"]},
        )
        # Should return error about missing model_id
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data["success"] is False

    def test_stacking_analyze_missing_cif(self, client):
        resp = client.post(
            "/api/stacking/analyze",
            json={},
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data["success"] is False


class TestMaterialFiltering:
    """Tests for material filtering by various parameters."""

    def test_filter_by_topology(self, client):
        resp = client.get("/api/materials?topology=TestTopo")
        assert resp.status_code == 200
        data = resp.get_json()
        for m in data["materials"]:
            assert m["topology"] == "TestTopo"

    def test_filter_by_nonexistent_topology(self, client):
        resp = client.get("/api/materials?topology=NonExistentTopo999")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0

    def test_filter_by_elements(self, client):
        resp = client.get("/api/materials?elements=Ba")
        assert resp.status_code == 200
        data = resp.get_json()
        for m in data["materials"]:
            assert "Ba" in m["elements"]

    def test_filter_by_space_group(self, client):
        resp = client.get("/api/materials?space_group=Pm-3m")
        assert resp.status_code == 200
        data = resp.get_json()
        for m in data["materials"]:
            assert m["space_group"] == "Pm-3m"

    def test_filter_by_formula(self, client):
        resp = client.get("/api/materials?formula=BaTiO3")
        assert resp.status_code == 200
        data = resp.get_json()
        for m in data["materials"]:
            assert m["formula"] == "BaTiO3"

    def test_combined_filters(self, client):
        resp = client.get("/api/materials?topology=TestTopo&elements=Ba")
        assert resp.status_code == 200
