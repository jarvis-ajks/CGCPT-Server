#!/usr/bin/env python3
"""
CGCPT 数据备份与恢复工具
"""

import os
import sys
import json
import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logger import get_logger

logger = get_logger(__name__)


def backup_database(backup_dir: Path = None) -> Optional[Path]:
    """Backup MySQL database using mysqldump with secure credential handling.

    Creates a gzipped SQL dump of the database. Password is passed via a
    temporary ``--defaults-extra-file`` so it never appears in the process
    list.

    Args:
        backup_dir: Directory to store the backup file. Defaults to
            ``PROJECT_ROOT / "backups"``.

    Returns:
        Path to the backup file on success, or ``None`` on failure or when
        the database is not MySQL.
    """
    import subprocess
    from config import DATABASE_URL

    if backup_dir is None:
        backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"cgcpt_db_{timestamp}.sql.gz"

    if "mysql" not in str(DATABASE_URL):
        logger.warning("Not using MySQL, skipping SQL backup")
        return None

    try:
        from urllib.parse import urlparse

        url = urlparse(DATABASE_URL)
        db_name = url.path.lstrip("/")
        user = url.username or "cgcpt"
        password = url.password or ""
        host = url.hostname or "localhost"
        port = url.port or 3306

        # Use defaults-extra-file to avoid exposing password in process list
        import tempfile

        cnf_file = None
        try:
            cnf_fd, cnf_path = tempfile.mkstemp(suffix=".cnf")
            cnf_file = Path(cnf_path)
            with os.fdopen(cnf_fd, "w") as f:
                f.write(f"[client]\nuser={user}\npassword={password}\nhost={host}\nport={port}\n")

            cmd = [
                "mysqldump",
                f"--defaults-extra-file={cnf_path}",
                db_name,
            ]

            logger.info("Backing up database to %s...", backup_file)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with gzip.open(backup_file, "wb") as f:
                for chunk in iter(lambda: proc.stdout.read(8192), b""):
                    f.write(chunk)
            proc.wait()
        finally:
            if cnf_file and cnf_file.exists():
                cnf_file.unlink()

        if proc.returncode == 0:
            logger.info("Database backup complete: %s", backup_file)
            return backup_file
        else:
            logger.error("mysqldump failed: %s", proc.stderr.read().decode())
            return None
    except Exception as e:
        logger.error("Database backup failed: %s", e)
        return None


def export_materials(output_file: Path = None) -> Optional[Path]:
    """导出材料数据到 JSON。

    Args:
        output_file: 输出文件路径。默认为 ``PROJECT_ROOT / "exports" / materials_<timestamp>.json``。

    Returns:
        成功时返回输出文件路径，失败时返回 ``None``。
    """
    from models import SessionLocal, Material

    if output_file is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / "exports" / f"materials_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    logger.info("Exporting materials to %s...", output_file)
    db = SessionLocal()
    try:
        materials = db.query(Material).all()
        data: List[Dict[str, Any]] = []
        for m in materials:
            data.append(
                {
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
                }
            )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(data),
                    "materials": data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info("Exported %d materials", len(data))
        return output_file
    except Exception as e:
        logger.error("Export materials failed: %s", e)
        return None
    finally:
        db.close()


def export_prototypes(output_file: Path = None) -> Optional[Path]:
    """导出原型数据到 JSON。

    Args:
        output_file: 输出文件路径。默认为 ``PROJECT_ROOT / "exports" / prototypes_<timestamp>.json``。

    Returns:
        成功时返回输出文件路径，失败时返回 ``None``。
    """
    from models import SessionLocal, Prototype

    if output_file is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / "exports" / f"prototypes_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    logger.info("Exporting prototypes to %s...", output_file)
    db = SessionLocal()
    try:
        protos = db.query(Prototype).all()
        data: List[Dict[str, Any]] = []
        for p in protos:
            data.append(
                {
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
                }
            )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(data),
                    "prototypes": data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info("Exported %d prototypes", len(data))
        return output_file
    except Exception as e:
        logger.error("Export prototypes failed: %s", e)
        return None
    finally:
        db.close()


def main() -> None:
    """CLI 入口：支持 backup 和 export 子命令。"""
    import argparse

    parser = argparse.ArgumentParser(description="CGCPT Data Management Tool")
    subparsers = parser.add_subparsers(title="Commands", dest="cmd")

    # Backup command
    subparsers.add_parser("backup", help="Backup database and data")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument(
        "type", choices=["all", "materials", "prototypes"], help="Type of data to export"
    )

    args = parser.parse_args()

    if args.cmd == "backup":
        logger.info("=== CGCPT Backup ===")
        backup_database()
        export_materials()
        export_prototypes()
        logger.info("=== Backup complete ===")

    elif args.cmd == "export":
        if args.type in ["all", "materials"]:
            export_materials()
        if args.type in ["all", "prototypes"]:
            export_prototypes()
        logger.info("=== Export complete ===")


if __name__ == "__main__":
    main()
