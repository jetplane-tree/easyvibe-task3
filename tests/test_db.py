# tests/test_db.py
import os
import tempfile
from data.db import Database


def test_database_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "materials" in tables
        assert "generation_history" in tables
        db.close()


def test_save_and_get_material():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("测试商品", ["卖点1", "卖点2"], 99.9, "/fake/path.png")
        assert mid > 0
        material = db.get_material(mid)
        assert material["name"] == "测试商品"
        assert material["price"] == 99.9
        db.close()


def test_list_materials():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        db.save_material("商品A", ["卖点"], 10, "/a.png")
        db.save_material("商品B", ["卖点"], 20, "/b.png")
        materials = db.list_materials()
        assert len(materials) == 2
        db.close()


def test_search_materials():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        db.save_material("运动鞋A", ["透气"], 100, "/a.png")
        db.save_material("连衣裙B", ["显瘦"], 200, "/b.png")
        results = db.search_materials("运动")
        assert len(results) == 1
        assert results[0]["name"] == "运动鞋A"
        db.close()


def test_delete_material():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("商品", ["卖点"], 10, "/a.png")
        db.delete_material(mid)
        assert db.get_material(mid) is None
        db.close()


def test_save_and_list_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(os.path.join(tmpdir, "test.db"))
        mid = db.save_material("商品", ["卖点"], 10, "/a.png")
        hid = db.save_history(mid, "促销爆款", "taobao", "promo", "/out.png", [{"title": "T", "selling_points": ["S"]}])
        assert hid > 0
        history = db.list_history()
        assert len(history) == 1
        assert history[0]["template_name"] == "促销爆款"
        db.close()
