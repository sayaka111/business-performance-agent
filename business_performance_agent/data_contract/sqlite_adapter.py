"""Read-only Olist adapter. Physical fields are confined to this data boundary."""
import json
import hashlib
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from .adapter import DatasetAdapter
from ..config.settings import ReadOnlyPolicy
from ..models.schemas import BoundaryError, Period
from ..tools.calculations import evaluate_formula


@lru_cache(maxsize=200000)
def iso_day(value):
    if not value:
        return None
    for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError('Malformed source timestamp')


class SQLiteDatasetAdapter(DatasetAdapter):
    COLUMNS = {
        'orders': ('order_id', 'customer_id', 'order_approved_at', 'order_status'),
        'order_items': ('order_id', 'order_item_id', 'product_id', 'price'),
        'customers': ('customer_id', 'customer_unique_id'),
        'products': ('product_id', 'product_category_name'),
    }

    def __init__(self, knowledge, database, policy=None):
        self.knowledge = knowledge
        self.path = Path(database).resolve()
        self.fingerprint = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self._file_signature = (self.path.stat().st_size, self.path.stat().st_mtime_ns)
        self.mapping = json.loads(Path(__file__).with_name('olist_mapping.json').read_text(encoding='utf-8'))
        self.capabilities = self.mapping['capabilities']
        self.policy = policy or ReadOnlyPolicy(query_timeout=15, max_rows=250000,
            table_allowlist=tuple(self.COLUMNS), column_allowlist=tuple(f'{t}.{c}' for t, cols in self.COLUMNS.items() for c in cols))
        self.operations = []
        self._cache = {}
        self._cache_sources = {}
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            for table, columns in self.COLUMNS.items():
                actual = {row[1] for row in db.execute('PRAGMA table_info(' + table + ')')}
                if not set(columns) <= actual:
                    raise BoundaryError('data_unavailable', 'SQLite schema missing required source columns: ' + table)

    def _select(self, sql, parameters=()):
        self._check_snapshot()
        if not re.match(r'^\s*(SELECT|WITH)\b', sql, re.I):
            raise BoundaryError('data_unavailable', 'Only SELECT / WITH SELECT allowed')
        if self.policy.query_timeout <= 0 or self.policy.max_rows <= 0:
            raise BoundaryError('data_unavailable', 'Invalid query limits')
        started = time.monotonic()
        event = {'query_id': f'SQL{len(self.operations)+1:05d}', 'sql': sql, 'parameters': list(parameters), 'read_only': True, 'status': 'failed'}
        self.operations.append(event)
        def authorize(action, arg1, arg2, *_):
            if action == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK if arg1 in self.policy.table_allowlist and (not arg2 or f'{arg1}.{arg2}' in self.policy.column_allowlist) else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and arg2 in ('iso_day', 'count', 'min', 'max'):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        try:
            with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                db.create_function('iso_day', 1, iso_day, deterministic=True)
                db.set_authorizer(authorize)
                db.set_progress_handler(lambda: int(time.monotonic() - started > self.policy.query_timeout), 1000)
                result = db.execute(sql, parameters).fetchmany(self.policy.max_rows + 1)
                if len(result) > self.policy.max_rows:
                    raise BoundaryError('data_unavailable', 'max_rows exceeded; no truncation permitted')
            if time.monotonic() - started > self.policy.query_timeout:
                raise BoundaryError('data_unavailable', 'query_timeout')
            event.update(status='success', returned_rows=len(result))
            return result
        except sqlite3.Error:
            raise BoundaryError('data_unavailable', 'SQLite query denied, timed out, or invalid source data') from None

    def _check_snapshot(self):
        current = self.path.stat()
        if (current.st_size, current.st_mtime_ns) != self._file_signature:
            raise BoundaryError('semantic_conflict', 'SQLite snapshot changed during analysis; restart against a stable database')

    def schema(self):
        return {k: list(v) for k, v in self.COLUMNS.items()}

    def scan_size(self):
        return self._select('SELECT COUNT(*) FROM order_items')[0][0]

    def required_fields(self, metric_id):
        metric = self.knowledge.get_metric(metric_id)
        fields = set(metric.get('required_fields', []))
        for dep in metric.get('required_metrics', []):
            fields.update(self.required_fields(dep))
        return fields

    def metric_available(self, metric_id):
        metric = self.knowledge.get_metric(metric_id)
        return metric.get('availability') != 'optional' and self.required_fields(metric_id) <= self.mapping['semantic_mapping'].keys()

    def dimension_available(self, dimension_id):
        self.knowledge.get_dimension(dimension_id)
        return dimension_id in self.mapping['semantic_mapping']

    def _facts(self, period):
        self._check_snapshot()
        period = Period(**period) if isinstance(period, dict) else period
        key = (period.start, period.end)
        if key not in self._cache:
            rows = self._select('''SELECT o.order_id, i.order_item_id, c.customer_unique_id,
                iso_day(o.order_approved_at), i.price, i.product_id, p.product_category_name
                FROM orders o LEFT JOIN order_items i ON i.order_id=o.order_id
                LEFT JOIN customers c ON c.customer_id=o.customer_id
                LEFT JOIN products p ON p.product_id=i.product_id
                WHERE iso_day(o.order_approved_at) BETWEEN ? AND ?''', key)
            facts = []
            for oid, iid, customer, paid, price, product, category in rows:
                try:
                    amount = Decimal(price) if price is not None else None
                    if amount is not None and not amount.is_finite():
                        raise InvalidOperation
                except InvalidOperation:
                    raise BoundaryError('data_quality_boundary', 'Invalid merchandise amount') from None
                facts.append(dict(order_id=oid, order_item_id=json.dumps([oid, iid]) if iid else None,
                    customer_id=customer, paid_at=paid, payment_success=True, merchandise_amount=amount,
                    valid_order_item_merchandise_amount=amount, quantity=1 if iid else None,
                    product=product or 'unknown', category=category or 'unknown'))
            self._cache[key] = facts
            self._cache_sources[key] = self.operations[-1]['query_id']
        else:
            self.operations.append({'query_id': f'SQL{len(self.operations)+1:05d}', 'operation': 'cache_read',
                                    'source_query_id': self._cache_sources[key], 'read_only': True, 'status': 'success'})
        return self._cache[key]

    def _filtered(self, period, filters):
        for dimension, value in filters.items():
            if not self.dimension_available(dimension) or not isinstance(value, str):
                raise BoundaryError('data_unavailable', 'Unavailable dimension filter: ' + dimension)
        return [r for r in self._facts(period) if all(r[d] == v for d, v in filters.items())]

    def metric(self, metric_id, period, filters):
        if not self.metric_available(metric_id):
            raise BoundaryError('data_unavailable', 'Unavailable metric: ' + metric_id)
        definition = self.knowledge.get_metric(metric_id)
        if definition.get('required_metrics'):
            return evaluate_formula(definition['formula'], lambda dep: self.metric(dep, period, filters))
        match = re.fullmatch(r'(SUM|COUNT)\((DISTINCT )?(\w+)\)', definition['formula'])
        if not match:
            raise BoundaryError('data_unavailable', 'Unsupported Knowledge aggregate syntax')
        operation, distinct, field = match.groups()
        rows = self._filtered(period, filters)
        values = [r.get(field) for r in rows]
        if any(v is None for v in values):
            raise BoundaryError('data_quality_boundary', 'Required source values missing: ' + field)
        if operation == 'COUNT':
            return len(set(values)) if distinct else len(values)
        return float(sum(values, Decimal(0)))

    def segments(self, metric_id, dimension_id, period, filters):
        if not self.dimension_available(dimension_id):
            raise BoundaryError('data_unavailable', 'Unavailable dimension: ' + dimension_id)
        values = sorted({r[dimension_id] for r in self._filtered(period, filters)})
        return {v: self.metric(metric_id, period, dict(filters, **{dimension_id: v})) for v in values}

    def quality(self, scope):
        issues = []
        checks = {}
        def issue(name, severity, detail):
            issues.append(dict(type=name, severity=severity, detail=detail))
        for text in self.mapping['limitations']:
            issue('source_limitation', 'warning', text)
        fields = {'order_id', 'paid_at', 'payment_success'}
        for metric in scope['metrics']:
            fields.update(self.required_fields(metric))
        missing = fields - self.mapping['semantic_mapping'].keys()
        if missing:
            issue('missing_fields', 'blocked', 'Missing semantic mapping: ' + ','.join(sorted(missing)))
        checks['source_key_integrity'] = {}
        for table, keys in [('orders','order_id'), ('customers','customer_id'), ('products','product_id'), ('order_items','order_id,order_item_id')]:
            duplicates = self._select(f'SELECT COUNT(*) FROM (SELECT {keys} FROM {table} GROUP BY {keys} HAVING COUNT(*) > 1)')[0][0]
            checks['source_key_integrity'][table] = duplicates
            if duplicates:
                issue('duplicate_business_id', 'blocked', 'Duplicate source key in ' + table)
        bounds = self._select('SELECT MIN(iso_day(order_approved_at)), MAX(iso_day(order_approved_at)) FROM orders')[0]
        unknown_dates = self._select('SELECT COUNT(*) FROM orders o WHERE order_approved_at IS NULL AND EXISTS (SELECT 1 FROM order_items i WHERE i.order_id=o.order_id)')[0][0]
        if unknown_dates:
            issue('unattributable_payment_dates', 'blocked', f'{unknown_dates} item orders have no payment timestamp; overlap with requested periods cannot be excluded.')
        for label in ('current_period', 'baseline_period'):
            period = Period(**scope[label])
            if not bounds[0] or period.start <= bounds[0] or period.end >= bounds[1]:
                issue('incomplete_' + label, 'blocked', 'Period outside interior of observed payment dates')
            rows = self._filtered(period, scope.get('filters', {}))
            nulls = {f: sum(r.get(f) is None for r in rows) for f in fields - missing}
            checks[label] = {'rows': len(rows), 'null_counts': nulls}
            if any(nulls.values()):
                issue('missing_required_values', 'blocked', label + ': ' + str({k:v for k,v in nulls.items() if v}))
            ids = [r['order_item_id'] for r in rows if r['order_item_id'] is not None]
            if len(ids) != len(set(ids)):
                issue('duplicate_business_id', 'blocked', 'Duplicate order item key after joins')
            for dim in scope.get('dimensions', []):
                if not self.dimension_available(dim):
                    issue('unavailable_dimension', 'blocked', dim)
                elif any(r[dim] == 'unknown' for r in rows):
                    issue('unknown_dimension', 'warning', dim + ': unknown values retained')
        checks['observed_date_range'] = list(bounds)
        checks['optional_capability_availability'] = dict(self.capabilities)
        return {'issues': issues, 'checks': checks}
