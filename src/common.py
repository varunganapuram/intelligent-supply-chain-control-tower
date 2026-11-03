from pathlib import Path
import json
import os
import psycopg
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for folder in ('data/raw', 'data/processed', 'reports', 'artifacts', 'docs', 'powerbi', 'notebooks'):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

def load_env():
    p = ROOT / '.env'
    if p.exists():
        for line in p.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())

def connect():
    load_env()
    return psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'),
        port=os.getenv('PGPORT', '55432'), dbname=os.getenv('PGDATABASE', 'control_tower'),
        user=os.getenv('PGUSER', 'control_tower'), password=os.environ['PGPASSWORD'])

def query(sql):
    with connect() as con:
        with con.cursor() as cur:
            cur.execute(sql)
            return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])

def write_json(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding='utf-8')

def publish_frame(name, frame):
    """Publish generated facts atomically; retained numeric/date types."""
    from psycopg import sql
    frame.to_parquet(ROOT / 'data/processed' / f'{name}.parquet', index=False)
    frame.to_csv(ROOT / 'reports' / f'{name}.csv', index=False)
    types = []
    for col, dt in frame.dtypes.items():
        typ = 'timestamp' if pd.api.types.is_datetime64_any_dtype(dt) else 'boolean' if pd.api.types.is_bool_dtype(dt) else 'bigint' if pd.api.types.is_integer_dtype(dt) else 'double precision' if pd.api.types.is_numeric_dtype(dt) else 'text'
        types.append(sql.SQL('{} {}').format(sql.Identifier(col), sql.SQL(typ)))
    with connect() as con, con.cursor() as cur:
        cur.execute(sql.SQL('drop table if exists marts.{}').format(sql.Identifier(name)))
        cur.execute(sql.SQL('create table marts.{} ({})').format(sql.Identifier(name), sql.SQL(',').join(types)))
        with cur.copy(sql.SQL('copy marts.{} from stdin with (format csv, header true)').format(sql.Identifier(name))) as cp:
            cp.write(frame.to_csv(index=False))
