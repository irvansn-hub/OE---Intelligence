"""Penyimpanan PostgreSQL opsional. Demo tanpa database memakai data sintetis."""
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import os
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from database.schema import SCHEMA

ITEM = ("item_name", "category", "specification", "brand", "unit")
IDENTITY = (*ITEM, "quantity", "price", "region", "location", "source_type", "source_name",
            "vendor", "observation_date", "effective_year", "effective_date", "version",
            "url_reference", "notes", "is_demo")


def evidence_key(row):
    values = [str(row.get(key, "")).strip().casefold() for key in IDENTITY]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def as_json(value):
    return json.loads(json.dumps(value, default=lambda x: x.isoformat(), allow_nan=False))


def make_observation(row):
    key = evidence_key(row)
    return {
        **row, "price_observation_id": key, "fingerprint": key,
        "normalized_unit_price": row["price"], "created_at": datetime.now().astimezone(),
    }


def summary(snapshot):
    return {key: snapshot[key] for key in ("analysis_id", "context", "result", "actual_unit_price")}


class PostgresRepository:
    def __init__(self, dsn):
        self.dsn = dsn

    @contextmanager
    def connect(self):
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5) as con:
            yield con

    def initialize(self, workspace):
        with self.connect() as con:
            con.execute("SELECT pg_advisory_xact_lock(723629::bigint)")
            con.execute(SCHEMA)
            if con.execute("SELECT 1 FROM initialization WHERE name='vercel-demo-v1'").fetchone():
                return
            self.write_prices(con, workspace["prices"])
            self.write_indices(con, workspace["indices"])
            for snapshot in workspace["analyses"]:
                self.write_analysis(con, snapshot)
            con.execute("INSERT INTO initialization VALUES ('vercel-demo-v1')")

    @staticmethod
    def write_prices(con, rows):
        imported = {}
        for row in rows:
            key = row["fingerprint"]
            old = con.execute(
                "SELECT * FROM observation_details WHERE fingerprint=%s", (key,)
            ).fetchone()
            if old:
                imported[key] = old
                continue
            item = con.execute(
                """INSERT INTO items (item_id,item_name,category,specification,brand,unit)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (item_name,category,specification,brand,unit)
                   DO UPDATE SET item_name=EXCLUDED.item_name RETURNING item_id""",
                (str(uuid4()), *(row[k] for k in ITEM)),
            ).fetchone()
            source = con.execute(
                """INSERT INTO reference_sources (source_id,source_type,source_name,source_year,version,effective_date)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (source_type,source_name,source_year,version)
                   DO UPDATE SET source_name=EXCLUDED.source_name RETURNING source_id,effective_date""",
                (str(uuid4()), *(row[k] for k in ("source_type", "source_name", "effective_year", "version", "effective_date"))),
            ).fetchone()
            if str(source["effective_date"]) != str(row["effective_date"]):
                raise ValueError("Tanggal efektif berbeda untuk sumber dan versi yang sama. Gunakan versi baru.")
            con.execute(
                """INSERT INTO price_observations
                (price_observation_id,item_id,source_id,vendor,quantity,price,normalized_unit_price,location,
                 region,observation_date,url_reference,notes,is_demo,fingerprint,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (fingerprint) DO NOTHING""",
                (row["price_observation_id"], item["item_id"], source["source_id"],
                 *(row[k] for k in ("vendor", "quantity", "price", "normalized_unit_price", "location",
                                    "region", "observation_date", "url_reference", "notes",
                                    "is_demo", "fingerprint", "created_at"))),
            )
            imported[key] = con.execute(
                "SELECT * FROM observation_details WHERE fingerprint=%s", (key,)
            ).fetchone()
        return list(imported.values())

    @staticmethod
    def write_indices(con, rows):
        for row in rows:
            inserted = con.execute(
                """INSERT INTO inflation_indices (index_name,year,adjustment_rate,is_demo)
                   VALUES (%s,%s,%s,TRUE) ON CONFLICT DO NOTHING RETURNING adjustment_rate""",
                (row["index_name"], row["year"], row["adjustment_rate"]),
            ).fetchone()
            if inserted is None:
                previous = con.execute(
                    "SELECT adjustment_rate FROM inflation_indices WHERE index_name=%s AND year=%s AND is_demo",
                    (row["index_name"], row["year"]),
                ).fetchone()
                if previous["adjustment_rate"] != row["adjustment_rate"]:
                    raise ValueError("Tahun dan nama indeks sudah ada. Gunakan nama versi baru untuk revisi.")
        return rows

    @staticmethod
    def write_analysis(con, snapshot):
        context, result = snapshot["context"], snapshot["result"]
        key = snapshot["analysis_id"]
        con.execute(
            """INSERT INTO analyses
              (analysis_id,analysis_name,item_name,analysis_date,target_date,benchmark,actual_unit_price,
               observation_count,outlier_count,is_demo,snapshot)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s) ON CONFLICT DO NOTHING""",
            (key, context["analysis_name"], context["item_name"], context["analysis_date"], context["target_date"],
             result["benchmark"], snapshot["actual_unit_price"], result["stats"]["n"],
             result["outlier_count"], Jsonb(snapshot)),
        )
        with con.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO analysis_observations
                   (analysis_id,price_observation_id,decision,justification,is_comparable,is_outlier,evidence_snapshot)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                [(key, row["price_observation_id"], row["decision"], row["justification"],
                  row["is_comparable"], row["is_outlier"], Jsonb(row)) for row in snapshot["evidence"]],
            )

    def import_prices(self, rows):
        with self.connect() as con:
            return self.write_prices(con, rows)

    def import_indices(self, rows):
        with self.connect() as con:
            return self.write_indices(con, rows)

    def save_analysis(self, snapshot):
        with self.connect() as con:
            self.write_analysis(con, snapshot)

    def prices(self, keys):
        with self.connect() as con:
            return con.execute("SELECT * FROM observation_details WHERE is_demo AND price_observation_id=ANY(%s)",
                               (keys,)).fetchall()

    def indices(self):
        with self.connect() as con:
            return con.execute("SELECT * FROM inflation_indices WHERE is_demo ORDER BY index_name,year DESC").fetchall()

    def load_analysis(self, key):
        with self.connect() as con:
            row = con.execute("SELECT snapshot FROM analyses WHERE analysis_id=%s AND is_demo", (key,)).fetchone()
            return row["snapshot"] if row else None

    def workspace(self):
        with self.connect() as con:
            observations = con.execute(
                "SELECT * FROM observation_details WHERE is_demo ORDER BY observation_date DESC LIMIT 2001"
            ).fetchall()
            saved = con.execute(
                "SELECT snapshot - 'evidence' AS summary FROM analyses WHERE is_demo ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        return {"prices": observations[:2000], "truncated": len(observations) > 2000,
                "indices": self.indices(), "analyses": [row["summary"] for row in saved]}


@lru_cache(maxsize=1)
def repository():
    dsn = os.environ.get("HPS_DATABASE_URL")
    if not dsn:
        return None
    from database.demo import demo_workspace

    repo = PostgresRepository(dsn)
    repo.initialize(demo_workspace())
    return repo
