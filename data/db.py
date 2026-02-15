# data/db.py
import sqlite3
import json
import os


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "app.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                selling_points TEXT,
                price REAL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER REFERENCES materials(id),
                template_name TEXT,
                platform TEXT,
                copy_style TEXT,
                generated_image_path TEXT,
                generated_copy TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def save_material(self, name: str, selling_points: list, price: float, image_path: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO materials (name, selling_points, price, image_path) VALUES (?, ?, ?, ?)",
            (name, json.dumps(selling_points, ensure_ascii=False), price, image_path),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_material(self, material_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
        return d

    def list_materials(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM materials ORDER BY created_at DESC").fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
            results.append(d)
        return results

    def search_materials(self, keyword: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM materials WHERE name LIKE ? ORDER BY created_at DESC",
            (f"%{keyword}%",),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["selling_points"] = json.loads(d["selling_points"]) if d["selling_points"] else []
            results.append(d)
        return results

    def update_material(self, material_id: int, **kwargs):
        allowed = {"name", "selling_points", "price", "image_path"}
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                if k == "selling_points":
                    v = json.dumps(v, ensure_ascii=False)
                updates.append(f"{k} = ?")
                values.append(v)
        if updates:
            values.append(material_id)
            self.conn.execute(f"UPDATE materials SET {', '.join(updates)} WHERE id = ?", values)
            self.conn.commit()

    def delete_material(self, material_id: int):
        self.conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        self.conn.commit()

    def save_history(self, material_id: int, template_name: str, platform: str,
                     copy_style: str, image_path: str, copies: list) -> int:
        cursor = self.conn.execute(
            "INSERT INTO generation_history (material_id, template_name, platform, copy_style, generated_image_path, generated_copy) VALUES (?, ?, ?, ?, ?, ?)",
            (material_id, template_name, platform, copy_style, image_path, json.dumps(copies, ensure_ascii=False)),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT h.*, m.name as product_name FROM generation_history h LEFT JOIN materials m ON h.material_id = m.id ORDER BY h.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["generated_copy"] = json.loads(d["generated_copy"]) if d["generated_copy"] else []
            results.append(d)
        return results

    def close(self):
        self.conn.close()
