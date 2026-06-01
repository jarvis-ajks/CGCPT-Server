#!/usr/bin/env python3
"""
CGCPT 数据备份与恢复工具
"""

import os
import sys
import json
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目路径
PROJECT_ROOT = Path("/opt/CGCPT")
sys.path.insert(0, str(PROJECT_ROOT))


def backup_database(backup_dir: Path = None) -> Path:
    """备份 MySQL 数据库"""
    import subprocess
    from models import DATABASE_URL

    if backup_dir is None:
        backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"cgcpt_db_{timestamp}.sql.gz"

    # 解析数据库连接信息
    if "mysql" not in str(DATABASE_URL):
        print("WARNING: Not using MySQL, skipping SQL backup")
        return None

    try:
        from urllib.parse import urlparse
        url = urlparse(DATABASE_URL)
        db_name = url.path.lstrip("/")
        user = url.username or "cgcpt"
        password = url.password or ""
        host = url.hostname or "localhost"
        port = url.port or 3306

        # 使用 mysqldump 备份
        cmd = [
            "mysqldump",
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            f"--password={password}",
            db_name,
        ]

        print(f"Backing up database to {backup_file}...")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(backup_file, "wb") as f:
            for chunk in iter(lambda: proc.stdout.read(8192), b""):
                f.write(chunk)
        proc.wait()

        if proc.returncode == 0:
            print(f"✓ Database backup complete: {backup_file}")
            return backup_file
        else:
            print(f"ERROR: mysqldump failed: {proc.stderr.read().decode()}")
            return None
    except Exception as e:
        print(f"ERROR: Database backup failed: {e}")
        return None


def export_materials(output_file: Path = None) -> Path:
    """导出材料数据到 JSON"""
    from models import SessionLocal, Material

    if output_file is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / "exports" / f"materials_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    print(f"Exporting materials to {output_file}...")
    db = SessionLocal()
    try:
        materials = db.query(Material).all()
        data = []
        for m in materials:
            data.append({
                "id": m.id,
                "formula": m.formula,
                "space_group": m.space_group,
                "topology_id": m.topology_id,
                "elements": m.elements,
                "lattice_a": m.lattice_a,
                "lattice_b": m.lattice_b,
                "lattice_c": m.lattice_c,
                "lattice_alpha": m.lattice_alpha,
                "lattice_beta": m.lattice_beta,
                "lattice_gamma": m.lattice_gamma,
                "n_atoms": m.n_atoms,
                "is_verified": m.is_verified,
                "source": m.source,
                "cif_path": m.cif_path,
                "cif_content": m.cif_content,
                "metadata_json": m.metadata_json,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            })

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "exported_at": datetime.utcnow().isoformat(),
                "count": len(data),
                "materials": data,
            }, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported {len(data)} materials")
        return output_file
    finally:
        db.close()


def export_prototypes(output_file: Path = None) -> Path:
    """导出原型数据到 JSON"""
    from models import SessionLocal, Prototype

    if output_file is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / "exports" / f"prototypes_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    print(f"Exporting prototypes to {output_file}...")
    db = SessionLocal()
    try:
        protos = db.query(Prototype).all()
        data = []
        for p in protos:
            data.append({
                "id": p.id,
                "prototype_id": p.prototype_id,
                "expanded_modes": p.expanded_modes,
                "reference_grid": p.reference_grid,
                "ideal_space_group": p.ideal_space_group,
                "space_group_number": p.space_group_number,
                "crystal_system": p.crystal_system,
                "is_neutral": p.is_neutral,
                "topology_data": p.topology_data,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "exported_at": datetime.utcnow().isoformat(),
                "count": len(data),
                "prototypes": data,
            }, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported {len(data)} prototypes")
        return output_file
    finally:
        db.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CGCPT Data Management Tool")
    subparsers = parser.add_subparsers(title="Commands", dest="cmd")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup database and data")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("type", choices=["all", "materials", "prototypes"],
                               help="Type of data to export")

    args = parser.parse_args()

    if args.cmd == "backup":
        print("=== CGCPT Backup ===")
        backup_database()
        export_materials()
        export_prototypes()
        print("=== Backup complete ===")

    elif args.cmd == "export":
        if args.type in ["all", "materials"]:
            export_materials()
        if args.type in ["all", "prototypes"]:
            export_prototypes()
        print("=== Export complete ===")


if __name__ == "__main__":
    main()
