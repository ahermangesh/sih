#!/usr/bin/env python3
"""
Parallel Complete NetCDF Extractor for FloatChat
================================================

Processes ARGO NetCDF files in parallel and writes:
- Float metadata (upsert on wmo_id)
- Profile rows (upsert on (float_id, profile_number))
- Measurements (delete-then-bulk-insert per profile)

Optimizations:
- Separate DB connection per worker process
- Chunked bulk inserts via psycopg2.extras.execute_values
- Streaming progress logs

Run:
  python parallel_complete_extractor.py --data ./argo_data --procs 6 --batch-size 25 --max-files 200
"""

import argparse
import glob
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import numpy as np
import psycopg2
import psycopg2.extras
import structlog
import xarray as xr
from multiprocessing import Pool, cpu_count


logger = structlog.get_logger(__name__)

# Default DB URL; can be overridden with --db
DEFAULT_DB_URL = (
    "postgresql://floatchat_user:floatchat_secure_2025@localhost:5432/floatchat_db"
)


def ensure_schema(db_url: str) -> None:
    """Ensure required unique indexes exist for upserts."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            # Unique index to allow ON CONFLICT for profiles
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_float_profile
                ON argo_profiles (float_id, profile_number);
                """
            )
            # Helpful indexes for measurements
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_measurements_profile_id
                ON argo_measurements (profile_id);
                """
            )
        logger.info("🔧 Schema/indexes ensured for parallel extractor")
    finally:
        conn.close()


def _decode_str_array(value: Any) -> str:
    if isinstance(value, np.ndarray):
        return "".join(
            [x.decode("utf-8") if isinstance(x, (bytes, np.bytes_)) else str(x) for x in value.flat]
        ).strip()
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8").strip()
    return str(value).strip()


def extract_file(file_path: str) -> Dict[str, Any]:
    """Extract float, profile and measurement data from a NetCDF file.

    Returns a dict with keys: float, profiles, measurements.
    profiles: List[Dict] with profile_number etc.
    measurements: List[Tuple(profile_number, pressure, depth, temperature, salinity,
                             pressure_qc, temperature_qc, salinity_qc)]
    """
    with xr.open_dataset(file_path, decode_times=False) as ds:
        # Float metadata
        wmo_str = _decode_str_array(ds["PLATFORM_NUMBER"].values)
        wmo_id = int(wmo_str) if wmo_str.isdigit() else abs(hash(file_path)) % 1_000_000

        # Reference date
        try:
            ref_str = _decode_str_array(ds["REFERENCE_DATE_TIME"].values)
            ref_date = datetime.strptime(ref_str, "%Y%m%d%H%M%S")
        except Exception:
            ref_date = datetime(1950, 1, 1)

        # Deployment coordinates (from first values)
        try:
            lat0 = float(np.asarray(ds["LATITUDE"].values).flat[0])
            lon0 = float(np.asarray(ds["LONGITUDE"].values).flat[0])
        except Exception:
            lat0 = 0.0
            lon0 = 0.0

        float_row = {
            "wmo_id": wmo_id,
            "platform_type": "ARGO_FLOAT",
            "deployment_date": ref_date,
            "deployment_latitude": lat0,
            "deployment_longitude": lon0,
            "status": "ACTIVE",
        }

        n_prof = int(ds.sizes.get("N_PROF", 1))
        n_levels = int(ds.sizes.get("N_LEVELS", 0))

        profiles: List[Dict[str, Any]] = []
        measurements: List[Tuple[Any, ...]] = []

        # Pull arrays once for speed
        JULD = np.asarray(ds["JULD"].values) if "JULD" in ds.variables else None
        LAT = np.asarray(ds["LATITUDE"].values) if "LATITUDE" in ds.variables else None
        LON = np.asarray(ds["LONGITUDE"].values) if "LONGITUDE" in ds.variables else None
        CYCLE = (
            np.asarray(ds["CYCLE_NUMBER"].values) if "CYCLE_NUMBER" in ds.variables else None
        )
        PRES = np.asarray(ds["PRES"].values) if "PRES" in ds.variables else None
        TEMP = np.asarray(ds["TEMP"].values) if "TEMP" in ds.variables else None
        PSAL = np.asarray(ds["PSAL"].values) if "PSAL" in ds.variables else None

        for p in range(n_prof):
            # Profile metadata
            p_date = ref_date
            if JULD is not None and JULD.size > p:
                try:
                    j = float(JULD.flat[p])
                    if not np.isnan(j) and j > 0:
                        p_date = ref_date + timedelta(days=j)
                except Exception:
                    pass

            plat = 0.0
            plon = 0.0
            try:
                if LAT is not None and LAT.size > p:
                    plat = float(LAT.flat[p])
                if LON is not None and LON.size > p:
                    plon = float(LON.flat[p])
            except Exception:
                pass

            cycle = None
            try:
                if CYCLE is not None and CYCLE.size > p:
                    cycle = int(CYCLE.flat[p])
            except Exception:
                pass

            profiles.append(
                {
                    "profile_number": p + 1,
                    "cycle_number": cycle,
                    "profile_date": p_date,
                    "latitude": plat,
                    "longitude": plon,
                    "position_qc": "1",
                    "profile_qc": "1",
                }
            )

            # Measurements per profile
            for lvl in range(n_levels):
                pr = None
                tm = None
                sa = None
                depth = None
                try:
                    if PRES is not None:
                        pr = float(PRES[p, lvl] if PRES.ndim == 2 else PRES[lvl])
                        if np.isnan(pr) or pr < 0:
                            pr = None
                        else:
                            depth = pr
                except Exception:
                    pr = None

                try:
                    if TEMP is not None:
                        tm = float(TEMP[p, lvl] if TEMP.ndim == 2 else TEMP[lvl])
                        if np.isnan(tm) or not (-5 <= tm <= 50):
                            tm = None
                except Exception:
                    tm = None

                try:
                    if PSAL is not None:
                        sa = float(PSAL[p, lvl] if PSAL.ndim == 2 else PSAL[lvl])
                        if np.isnan(sa) or not (0 <= sa <= 50):
                            sa = None
                except Exception:
                    sa = None

                if pr is None and tm is None and sa is None:
                    continue

                measurements.append(
                    (
                        p + 1,  # profile_number ref
                        pr,
                        depth,
                        tm,
                        sa,
                        "1",
                        "1",
                        "1",
                    )
                )

        return {
            "file": os.path.basename(file_path),
            "float": float_row,
            "profiles": profiles,
            "measurements": measurements,
        }


def upsert_float_get_id(cur: psycopg2.extensions.cursor, data: Dict[str, Any]) -> int:
    cur.execute(
        """
        INSERT INTO argo_floats (wmo_id, platform_type, deployment_date,
                                 deployment_latitude, deployment_longitude, status)
        VALUES (%(wmo_id)s, %(platform_type)s, %(deployment_date)s,
                %(deployment_latitude)s, %(deployment_longitude)s, %(status)s)
        ON CONFLICT (wmo_id) DO UPDATE SET
            platform_type = EXCLUDED.platform_type,
            deployment_date = COALESCE(EXCLUDED.deployment_date, argo_floats.deployment_date),
            deployment_latitude = EXCLUDED.deployment_latitude,
            deployment_longitude = EXCLUDED.deployment_longitude,
            status = EXCLUDED.status
        RETURNING id
        """,
        data,
    )
    return cur.fetchone()[0]


def upsert_profiles_return_ids(
    cur: psycopg2.extensions.cursor, float_id: int, profiles: List[Dict[str, Any]]
) -> Dict[int, int]:
    """Upsert profiles and return mapping from profile_number->profile_id."""
    # Build list of tuples aligned with SQL order
    values = [
        (
            float_id,
            p["profile_number"],
            p["cycle_number"],
            p["profile_date"],
            p["latitude"],
            p["longitude"],
            p["position_qc"],
            p["profile_qc"],
        )
        for p in profiles
    ]

    # ON CONFLICT by (float_id, profile_number)
    sql = (
        "INSERT INTO argo_profiles (float_id, profile_number, cycle_number, profile_date, latitude, longitude, position_qc, profile_qc) "
        "VALUES %s ON CONFLICT (float_id, profile_number) DO UPDATE SET "
        "cycle_number = EXCLUDED.cycle_number, "
        "profile_date = EXCLUDED.profile_date, "
        "latitude = EXCLUDED.latitude, "
        "longitude = EXCLUDED.longitude, "
        "position_qc = EXCLUDED.position_qc, "
        "profile_qc = EXCLUDED.profile_qc "
        "RETURNING id, profile_number"
    )

    psycopg2.extras.execute_values(cur, sql, values, page_size=1000)
    rows = cur.fetchall()
    return {int(pn): int(pid) for (pid, pn) in rows}


def insert_measurements_bulk(
    cur: psycopg2.extensions.cursor,
    profile_id_map: Dict[int, int],
    measurements: List[Tuple[Any, ...]],
    chunk_size: int = 10_000,
) -> int:
    """Delete existing and bulk-insert measurements for provided profiles.

    Returns number of inserted rows.
    """
    if not measurements:
        return 0

    # Group by profile_number
    by_profile: Dict[int, List[Tuple[Any, ...]]] = {}
    for m in measurements:
        prof_num = int(m[0])
        by_profile.setdefault(prof_num, []).append(m)

    # Delete existing for these profile_ids
    profile_ids = [profile_id_map[pn] for pn in by_profile.keys() if pn in profile_id_map]
    if profile_ids:
        cur.execute(
            "DELETE FROM argo_measurements WHERE profile_id = ANY(%s)", (profile_ids,)
        )

    total_inserted = 0
    template = "(%s, %s, %s, %s, %s, %s, %s, %s)"
    insert_sql = (
        "INSERT INTO argo_measurements (profile_id, pressure, depth, temperature, salinity, "
        "pressure_qc, temperature_qc, salinity_qc) VALUES %s"
    )

    batch: List[Tuple[Any, ...]] = []
    for pn, rows in by_profile.items():
        pid = profile_id_map.get(pn)
        if not pid:
            continue
        for r in rows:
            # Replace profile_number with profile_id
            batch.append((pid, r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
            if len(batch) >= chunk_size:
                psycopg2.extras.execute_values(
                    cur, insert_sql, batch, template=template, page_size=5000
                )
                total_inserted += len(batch)
                batch.clear()

    if batch:
        psycopg2.extras.execute_values(
            cur, insert_sql, batch, template=template, page_size=5000
        )
        total_inserted += len(batch)

    return total_inserted


def process_file(args: Tuple[str, str]) -> Tuple[str, int, int, float]:
    """Worker: extract and write one file. Returns (file, profiles, measurements, seconds)."""
    file_path, db_url = args
    t0 = time.time()
    try:
        data = extract_file(file_path)
        conn = psycopg2.connect(db_url)
        try:
            with conn:
                with conn.cursor() as cur:
                    float_id = upsert_float_get_id(cur, data["float"])
                    profile_id_map = upsert_profiles_return_ids(cur, float_id, data["profiles"])
                    inserted = insert_measurements_bulk(cur, profile_id_map, data["measurements"])
        finally:
            conn.close()
        dt = time.time() - t0
        logger.info(
            "✅ File processed",
            file=os.path.basename(file_path),
            profiles=len(data["profiles"]),
            measurements=len(data["measurements"]),
            seconds=round(dt, 2),
        )
        return (os.path.basename(file_path), len(data["profiles"]), len(data["measurements"]), dt)
    except Exception as e:
        logger.error("❌ File failed", file=os.path.basename(file_path), error=str(e))
        return (os.path.basename(file_path), 0, 0, -1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel ARGO NetCDF extractor")
    parser.add_argument("--data", default="./argo_data", help="Root directory of NetCDF files")
    parser.add_argument("--db", default=DEFAULT_DB_URL, help="PostgreSQL URL")
    parser.add_argument("--procs", type=int, default=max(1, cpu_count() - 1))
    parser.add_argument("--batch-size", type=int, default=25, help="Files per dispatch batch")
    parser.add_argument("--max-files", type=int, default=0, help="Limit number of files (0=all)")
    args_ns = parser.parse_args()

    data_root: str = args_ns.data
    db_url: str = args_ns.db
    procs: int = max(1, args_ns.procs)
    batch_size: int = max(1, args_ns["batch_size"] if isinstance(args_ns, dict) else args_ns.batch_size)
    max_files: int = args_ns.max_files

    logger.info(
        "🚀 Starting parallel extraction",
        procs=procs,
        data_root=data_root,
    )

    ensure_schema(db_url)

    all_files: List[str] = []
    for year_dir in glob.glob(os.path.join(data_root, "*")):
        if os.path.isdir(year_dir):
            for month_dir in glob.glob(os.path.join(year_dir, "*")):
                if os.path.isdir(month_dir):
                    all_files.extend(glob.glob(os.path.join(month_dir, "*.nc")))

    if max_files and max_files > 0:
        all_files = all_files[:max_files]

    total = len(all_files)
    if total == 0:
        logger.warning("No NetCDF files found", data_root=data_root)
        return

    logger.info("📁 Files found", total=total)

    t0 = time.time()
    processed = 0
    failed = 0
    total_profiles = 0
    total_measurements = 0

    # Create work args
    work = [(fp, db_url) for fp in all_files]

    with Pool(processes=procs) as pool:
        for fname, profs, meas, dt in pool.imap_unordered(process_file, work, chunksize=batch_size):
            if dt >= 0:
                processed += 1
                total_profiles += profs
                total_measurements += meas
            else:
                failed += 1

            elapsed = time.time() - t0
            rate = processed / elapsed if elapsed > 0 else 0.0
            logger.info(
                "📈 Progress",
                processed=processed,
                failed=failed,
                total=total,
                rate=f"{rate:.2f} files/sec",
            )

    elapsed = time.time() - t0
    logger.info("🎉 Parallel extraction complete",
                processed=processed,
                failed=failed,
                total=total,
                seconds=round(elapsed, 2),
                profiles=total_profiles,
                measurements=total_measurements)


if __name__ == "__main__":
    main()


