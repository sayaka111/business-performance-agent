"""Lossless Olist staging and read-only source readiness audit.

This module never equates an approval timestamp with a finalized semantic mapping.
It does not filter orders or replace missing source facts.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .olist_import import quote

TABLES = {
    'orders': ('order_id',),
    'order_items': ('order_id', 'order_item_id'),
    'order_payments': ('order_id', 'payment_sequential'),
    'customers': ('customer_id',),
    'products': ('product_id',),
}


def import_raw(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(destination)) as db, db:
            db.execute('CREATE TABLE source_manifest (filename TEXT PRIMARY KEY, sha256 TEXT, row_count INTEGER)')
            for table, keys in TABLES.items():
                path = source / ('olist_' + table + '_dataset.csv')
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    fields = reader.fieldnames
                    if not fields or len(set(fields)) != len(fields) or not set(keys) <= set(fields):
                        raise ValueError('Invalid header: ' + path.name)
                    db.execute('CREATE TABLE ' + quote(table) + ' (' + ','.join(quote(f) + ' TEXT' for f in fields) + ')')
                    statement = 'INSERT INTO ' + quote(table) + ' VALUES (' + ','.join('?' for _ in fields) + ')'
                    count = 0
                    for row in reader:
                        if None in row or any(row[f] is None for f in fields) or any(not row[k] for k in keys):
                            raise ValueError('Malformed source row: ' + path.name)
                        db.execute(statement, [row[f] or None for f in fields])
                        count += 1
                if not count or before != hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError('Empty or changing source: ' + path.name)
                db.execute('CREATE UNIQUE INDEX ' + quote(table + '_key') + ' ON ' + quote(table) + '(' + ','.join(quote(k) for k in keys) + ')')
                db.execute('INSERT INTO source_manifest VALUES (?,?,?)', (path.name, before, count))
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def audit(path):
    """No row identifiers or source customer details are included in the report."""
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        queries = []
        def scalar(sql):
            queries.append({'sql': sql, 'read_only': True})
            return db.execute(sql).fetchone()[0]
        counts = {t: scalar('SELECT COUNT(*) FROM ' + quote(t)) for t in TABLES}
        checks = {
            'approved_without_items': scalar('SELECT COUNT(*) FROM orders o WHERE order_approved_at IS NOT NULL AND NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id=o.order_id)'),
            'approved_without_payment': scalar('SELECT COUNT(*) FROM orders o WHERE order_approved_at IS NOT NULL AND NOT EXISTS (SELECT 1 FROM order_payments p WHERE p.order_id=o.order_id)'),
            'item_orders_without_approval': scalar('SELECT COUNT(*) FROM orders o WHERE order_approved_at IS NULL AND EXISTS (SELECT 1 FROM order_items i WHERE i.order_id=o.order_id)'),
            'orphan_items': scalar('SELECT COUNT(*) FROM order_items i WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.order_id=i.order_id)'),
            'orders_without_customer': scalar('SELECT COUNT(*) FROM orders o WHERE NOT EXISTS (SELECT 1 FROM customers c WHERE c.customer_id=o.customer_id)'),
        }
        dates = []
        malformed = 0
        for (value,) in db.execute('SELECT order_approved_at FROM orders WHERE order_approved_at IS NOT NULL'):
            for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                try:
                    dates.append(datetime.strptime(value, fmt).isoformat())
                    break
                except ValueError:
                    continue
            else:
                malformed += 1
        checks['malformed_approval_timestamp'] = malformed
        issues = [{'type': name, 'severity': 'blocked', 'detail': f'{name}: {count}; source facts require reconciliation, not automatic imputation.'}
                  for name, count in checks.items() if count]
        return {'run_id': str(uuid4()), 'phase': 'source_readiness_audit',
                'data_source': 'SQLite', 'database': str(Path(path).resolve()),
                'production_database': False, 'row_counts': counts,
                'approval_range': [min(dates), max(dates)] if dates else [],
                'schema': {t: [dict(zip(('cid','name','type','notnull','default','pk'), row))
                               for row in db.execute('PRAGMA table_info(' + quote(t) + ')')] for t in TABLES},
                'checks': checks, 'issues': issues, 'query_operations': queries,
                'status': 'blocked' if issues else 'success',
                'semantic_mapping_validated': False,
                'limitations': ['Source readiness audit only; not a GMV Workflow result.',
                                'Customer lifetime history, delivery region and payment semantics need source contracts.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Import into a NEW local database; original CSVs stay unchanged')
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--trace-dir', type=Path, default=Path('logs'))
    args = parser.parse_args()
    try:
        if args.source:
            import_raw(args.source, args.database)
        result = audit(args.database)
        args.trace_dir.mkdir(parents=True, exist_ok=True)
        trace = args.trace_dir / (result['run_id'] + '.json')
        trace.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: v for k, v in result.items() if k not in ('schema', 'query_operations')}, ensure_ascii=False, indent=2))
        print('Trace: ' + str(trace.resolve()))
        return 1 if result['status'] == 'blocked' else 0
    except (OSError, ValueError, sqlite3.Error):
        parser.exit(2, 'Source import/audit failed; inspect paths, schema and unique keys.\n')


if __name__ == '__main__':
    raise SystemExit(main())
