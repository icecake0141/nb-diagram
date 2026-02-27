import io
import tempfile
import unittest
from pathlib import Path

import app as app_module
from app import (
    CableRow,
    app,
    build_device_graph,
    build_drawio_xml,
    init_storage,
    normalize_color,
    parse_cables_csv,
    resolve_data_path,
)


class AppLogicTests(unittest.TestCase):
    def test_normalize_color_accepts_hex_and_lowercases(self):
        self.assertEqual(normalize_color("#ABCDEF", "Cat6"), "#abcdef")

    def test_normalize_color_falls_back_when_invalid(self):
        fallback = normalize_color("blue", "Cat6")
        self.assertRegex(fallback, r"^#[0-9a-f]{6}$")

    def test_parse_cables_csv_extracts_row_and_defaults(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination A Type,"
            "Termination B Device,Termination B Name,Termination B Type,"
            "Type,Color,Rack A,Rack B,Location A,Location B\n"
            "sw1,xe-0/0/1,dcim.interface,srv1,eth0,dcim.interface,Cat6,#ABCDEF,R1,R2,DC1,DC1\n"
        ).encode("utf-8")

        rows, columns = parse_cables_csv(csv_bytes)

        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(columns["a_device"])
        self.assertIsNotNone(columns["b_port"])
        self.assertEqual(rows[0].a_endpoint, "sw1:xe-0/0/1")
        self.assertEqual(rows[0].b_endpoint, "srv1:eth0")
        self.assertEqual(rows[0].cable_type, "Cat6")
        self.assertEqual(rows[0].cable_color, "#abcdef")
        self.assertEqual(rows[0].domain, "data")
        self.assertEqual(rows[0].rack_a, "R1")
        self.assertEqual(rows[0].rack_b, "R2")

    def test_parse_cables_csv_infers_device_from_termination_text(self):
        csv_bytes = (
            "Termination A,Termination B,Type\n" "fw1:ge-0/0/0,sw1:xe-0/0/1,Fiber\n"
        ).encode("utf-8")

        rows, _ = parse_cables_csv(csv_bytes)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].a_device, "fw1")
        self.assertEqual(rows[0].a_interface, "ge-0/0/0")
        self.assertEqual(rows[0].b_device, "sw1")
        self.assertEqual(rows[0].b_interface, "xe-0/0/1")

    def test_build_device_graph_aggregates_links_between_devices(self):
        rows = [
            CableRow(
                a_device="sw1",
                a_interface="xe-0/0/1",
                b_device="srv1",
                b_interface="eth0",
                a_kind="interface",
                b_kind="power_port",
                cable_type="Cat6",
                cable_color="#123456",
                domain="power",
                rack_a="R1",
                rack_b="R2",
                edge_label="Cable-1 [Cat6]",
            ),
            CableRow(
                a_device="sw1",
                a_interface="xe-0/0/2",
                b_device="srv1",
                b_interface="eth1",
                a_kind="interface",
                b_kind="power_port",
                cable_type="Cat6",
                cable_color="#123456",
                domain="power",
                rack_a="R1",
                rack_b="R2",
                edge_label="Cable-2 [Cat6]",
            ),
        ]

        nodes, edges = build_device_graph(rows)

        self.assertEqual(len(nodes), 4)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["data"]["count"], 2)
        self.assertEqual(edges[0]["data"]["cable_type"], "Cat6")
        self.assertEqual(edges[0]["data"]["domain"], "power")
        rack_nodes = [n for n in nodes if n["data"]["node_type"] == "rack"]
        device_nodes = [n for n in nodes if n["data"]["node_type"] == "device"]
        self.assertEqual(len(rack_nodes), 2)
        self.assertEqual(len(device_nodes), 2)
        self.assertTrue(all(d["data"].get("parent", "").startswith("rack::") for d in device_nodes))

    def test_parse_cables_csv_does_not_use_termination_name_as_cable_label(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")

        rows, columns = parse_cables_csv(csv_bytes)

        self.assertEqual(len(rows), 1)
        self.assertIsNone(columns["cable_label"])
        self.assertEqual(rows[0].cable_label, "Cable-1")

    def test_parse_cables_csv_returns_empty_when_required_columns_missing(self):
        csv_bytes = ("foo,bar\n" "1,2\n").encode("utf-8")

        rows, columns = parse_cables_csv(csv_bytes)

        self.assertEqual(rows, [])
        self.assertIsNone(columns["a_device"])
        self.assertIsNone(columns["a_port"])
        self.assertIsNone(columns["b_device"])
        self.assertIsNone(columns["b_port"])

    def test_resolve_data_path_rejects_traversal(self):
        with self.assertRaises(ValueError):
            resolve_data_path("../outside.txt")

    def test_build_device_graph_role_hint_for_power_endpoints(self):
        rows = [
            CableRow(
                a_device="pdu1",
                a_interface="out1",
                b_device="srv1",
                b_interface="psu1",
                a_kind="power_outlet",
                b_kind="power_port",
                cable_type="Power",
                cable_color="#123456",
                domain="power",
            ),
            CableRow(
                a_device="ups1",
                a_interface="feed1",
                b_device="pdu2",
                b_interface="in1",
                a_kind="power_feed",
                b_kind="power_port",
                cable_type="Power",
                cable_color="#654321",
                domain="power",
            ),
        ]

        nodes, _ = build_device_graph(rows)
        by_id = {n["data"]["id"]: n["data"] for n in nodes if n["data"]["node_type"] == "device"}

        self.assertEqual(by_id["dev::pdu1"]["role_hint"], "pdu")
        self.assertEqual(by_id["dev::ups1"]["role_hint"], "power_source")
        self.assertEqual(by_id["dev::srv1"]["role_hint"], "powered_device")

    def test_build_drawio_xml_escapes_values_and_emits_edges(self):
        elements = [
            {
                "data": {
                    "id": "rack::R1",
                    "label": "R1",
                    "node_type": "rack",
                },
                "classes": "rack-group",
            },
            {
                "data": {
                    "id": "dev::sw1",
                    "label": 'sw<1>&"edge"',
                    "node_type": "device",
                    "role_hint": "leaf",
                    "rack": "R1",
                }
            },
            {
                "data": {
                    "id": "dev::srv1",
                    "label": "srv1",
                    "node_type": "device",
                    "role_hint": "server",
                    "rack": "R2",
                }
            },
            {
                "data": {
                    "id": "d1",
                    "source": "dev::sw1",
                    "target": "dev::srv1",
                    "label": "link<1>",
                    "color": "#0f766e",
                    "domain": "data",
                }
            },
        ]

        xml = build_drawio_xml(elements, diagram_name='Main & "Core"')

        self.assertIn('Main &amp; &quot;Core&quot;', xml)
        self.assertIn('sw&lt;1&gt;&amp;&quot;edge&quot;', xml)
        self.assertIn("link&lt;1&gt;", xml)
        self.assertIn('source="n1"', xml)
        self.assertIn('target="n2"', xml)
        self.assertNotIn(
            'value="R1" style="rounded=1;whiteSpace=wrap;html=1;fontColor=#ffffff;',
            xml,
        )
        self.assertIn("exitPerimeter=1;entryPerimeter=1;", xml)
        self.assertIn("exitX=", xml)
        self.assertIn("entryX=", xml)


class UploadSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = app_module.DATA_DIR
        self.original_upload_dir = app_module.UPLOAD_DIR
        self.original_result_dir = app_module.RESULT_DIR
        self.original_db_path = app_module.DB_PATH
        base = Path(self.temp_dir.name)
        app_module.DATA_DIR = base / "data"
        app_module.UPLOAD_DIR = app_module.DATA_DIR / "uploads"
        app_module.RESULT_DIR = app_module.DATA_DIR / "results"
        app_module.DB_PATH = app_module.DATA_DIR / "results.db"
        init_storage()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        app_module.DATA_DIR = self.original_data_dir
        app_module.UPLOAD_DIR = self.original_upload_dir
        app_module.RESULT_DIR = self.original_result_dir
        app_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_legacy_upload_endpoint_is_deprecated(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        response = self.client.post(
            "/upload",
            data={"csv_file": (io.BytesIO(csv_bytes), "legacy.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 410)
        self.assertIn("Legacy /upload is deprecated.", response.get_data(as_text=True))

    def test_upload_rejects_file_over_limit(self):
        too_large = b"a" * (app.config["MAX_CONTENT_LENGTH"] + 1)
        response = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(too_large), "too-large.csv")},
            content_type="multipart/form-data",
        )

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 413)
        self.assertIn("Uploaded file is too large. Maximum size is 5 MiB.", html)

    def test_api_import_endpoints(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        create_resp = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(csv_bytes), "api.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(create_resp.status_code, 201)
        body = create_resp.get_json()
        self.assertIsNotNone(body)
        assert body is not None
        self.assertIn("import_id", body)
        self.assertEqual(body["status"], "uploaded")
        self.assertIn("headers", body)
        import_id = body["import_id"]

        mapping_resp = self.client.put(
            f"/api/imports/{import_id}/mapping",
            json={"mapping": body["mapping_candidates"]},
        )
        self.assertEqual(mapping_resp.status_code, 200)

        execute_resp = self.client.post(f"/api/imports/{import_id}/execute")
        self.assertEqual(execute_resp.status_code, 200)
        execute_body = execute_resp.get_json()
        self.assertIsNotNone(execute_body)
        assert execute_body is not None
        self.assertEqual(execute_body["status"], "completed")

        get_resp = self.client.get(f"/api/imports/{import_id}")
        self.assertEqual(get_resp.status_code, 200)
        get_body = get_resp.get_json()
        self.assertIsNotNone(get_body)
        assert get_body is not None
        self.assertEqual(get_body["import_id"], import_id)
        self.assertEqual(get_body["status"], "completed")
        self.assertGreater(get_body["node_count"], 0)

    def test_api_graphs_and_exports_after_execute(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        create_resp = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(csv_bytes), "api-graph.csv")},
            content_type="multipart/form-data",
        )
        body = create_resp.get_json()
        self.assertIsNotNone(body)
        assert body is not None
        import_id = body["import_id"]
        self.client.put(
            f"/api/imports/{import_id}/mapping",
            json={"mapping": body["mapping_candidates"]},
        )
        self.client.post(f"/api/imports/{import_id}/execute")

        graph_resp = self.client.get(f"/api/graphs/{import_id}?view=device")
        self.assertEqual(graph_resp.status_code, 200)
        graph_body = graph_resp.get_json()
        self.assertIsNotNone(graph_body)
        assert graph_body is not None
        self.assertEqual(graph_body["view"], "device")
        self.assertGreater(len(graph_body["elements"]), 0)

        export_resp = self.client.get(f"/api/exports/{import_id}?format=drawio")
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn("application/xml", export_resp.content_type)

    def test_api_import_requires_file(self):
        response = self.client.post("/api/imports", data={}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)

    def test_api_graph_requires_completed_import(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        create_resp = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(csv_bytes), "api-state.csv")},
            content_type="multipart/form-data",
        )
        body = create_resp.get_json()
        self.assertIsNotNone(body)
        assert body is not None
        import_id = body["import_id"]

        graph_resp = self.client.get(f"/api/graphs/{import_id}?view=device")
        self.assertEqual(graph_resp.status_code, 409)

    def test_api_mapping_rejects_non_object(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        create_resp = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(csv_bytes), "api-map.csv")},
            content_type="multipart/form-data",
        )
        body = create_resp.get_json()
        self.assertIsNotNone(body)
        assert body is not None
        import_id = body["import_id"]

        map_resp = self.client.put(
            f"/api/imports/{import_id}/mapping",
            json={"mapping": "invalid"},
        )
        self.assertEqual(map_resp.status_code, 400)

    def test_api_exports_rejects_unknown_format(self):
        csv_bytes = (
            "Termination A Device,Termination A Name,Termination B Device,Termination B Name,Type\n"
            "sw1,xe-0/0/1,sw2,xe-0/0/2,Cat6\n"
        ).encode("utf-8")
        create_resp = self.client.post(
            "/api/imports",
            data={"csv_file": (io.BytesIO(csv_bytes), "api-export.csv")},
            content_type="multipart/form-data",
        )
        body = create_resp.get_json()
        self.assertIsNotNone(body)
        assert body is not None
        import_id = body["import_id"]
        self.client.put(
            f"/api/imports/{import_id}/mapping",
            json={"mapping": body["mapping_candidates"]},
        )
        self.client.post(f"/api/imports/{import_id}/execute")

        export_resp = self.client.get(f"/api/exports/{import_id}?format=foo")
        self.assertEqual(export_resp.status_code, 400)

    def test_openapi_endpoint_serves_spec(self):
        response = self.client.get("/api/openapi.yaml")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("openapi: 3.1.0", text)


if __name__ == "__main__":
    unittest.main()
