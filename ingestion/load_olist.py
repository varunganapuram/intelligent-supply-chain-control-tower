"""Download the public Olist archive, profile it, then COPY to isolated raw tables."""
import csv
import hashlib
import json
import io
import zipfile
import urllib.request
from pathlib import Path
import pandas as pd
from psycopg import sql
from src.common import ROOT, connect, write_json

FILES = {
    'orders': ('olist_orders_dataset.csv', ['order_id']),
    'order_items': ('olist_order_items_dataset.csv', ['order_id', 'order_item_id']),
    'customers': ('olist_customers_dataset.csv', ['customer_id']),
    'sellers': ('olist_sellers_dataset.csv', ['seller_id']),
    'products': ('olist_products_dataset.csv', ['product_id']),
    'order_payments': ('olist_order_payments_dataset.csv', ['order_id', 'payment_sequential']),
    'order_reviews': ('olist_order_reviews_dataset.csv', []),
    'geolocation': ('olist_geolocation_dataset.csv', []),
    'category_translation': ('product_category_name_translation.csv', ['product_category_name']),
}

def download(destination=None):
    target=Path(destination) if destination is not None else ROOT/'data/raw'
    target.mkdir(parents=True,exist_ok=True)
    if all((target / name).exists() for name, _ in FILES.values()):
        return
    url = 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce'
    with urllib.request.urlopen(url,timeout=180) as response:
        archive=response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name, _ in FILES.values():
            # Write only exact expected members, without trusting archive paths.
            (target / name).write_bytes(z.read(name))

def run():
    download()
    profiles = {}
    with connect() as con, con.cursor() as cur:
        cur.execute('create schema if not exists raw')
        for table, (filename, keys) in FILES.items():
            path = ROOT / 'data/raw' / filename
            frame = pd.read_csv(path, dtype=str)
            contract=json.loads((ROOT/'ingestion/source_schema.json').read_text())
            if list(frame.columns)!=contract[table]:
                raise ValueError(f'Source schema drift in {filename}; expected {contract[table]}, got {list(frame.columns)}')
            inferred=pd.read_csv(path,nrows=10000)
            profiles[table] = dict(file=filename, rows=len(frame), columns=list(frame),
                inferred_types_10k={c:str(dt) for c,dt in inferred.dtypes.items()},
                nulls=frame.isna().sum().to_dict(),
                duplicate_keys=int(frame.duplicated(keys).sum()) if keys else None,
                exact_duplicate_rows=int(frame.duplicated().sum()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            if keys and (frame[keys].isna().any().any() or frame.duplicated(keys).any()):
                raise ValueError(f'Invalid source key in {table}; see source file')
            cur.execute(sql.SQL('drop table if exists raw.{} cascade').format(sql.Identifier(table)))
            defs = sql.SQL(',').join(sql.SQL('{} text').format(sql.Identifier(c)) for c in frame.columns)
            cur.execute(sql.SQL('create table raw.{} ({})').format(sql.Identifier(table), defs))
            with cur.copy(sql.SQL('copy raw.{} from stdin with (format csv, header true)').format(sql.Identifier(table))) as cp:
                with path.open('rb') as source:
                    while block := source.read(1024 * 1024):
                        cp.write(block)
            print(f'Loaded {table}: {len(frame):,}', flush=True)
    write_json('reports/source_profile.json', profiles)
    write_json('reports/source_manifest.json', dict(source='https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce',
        license='CC BY-NC-SA 4.0', attribution='Olist and collaborators (2018)', files=profiles))
    return profiles

if __name__ == '__main__':
    run()
