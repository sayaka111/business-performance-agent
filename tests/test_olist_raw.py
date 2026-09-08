import csv
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from business_performance_agent.data_contract.olist_raw import import_raw, audit


class OlistRawTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'source.db'
        self.write('orders', ['order_id', 'customer_id', 'order_approved_at'], [['o1','c1','2018/2/1 8:00']])
        self.write('order_items', ['order_id', 'order_item_id'], [['o1','1']])
        self.write('order_payments', ['order_id', 'payment_sequential'], [['o1','1'],['o1','2']])
        self.write('customers', ['customer_id'], [['c1']])
        self.write('products', ['product_id'], [['p1']])

    def write(self, name, fields, rows):
        with (self.root / ('olist_' + name + '_dataset.csv')).open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            writer.writerows(rows)

    def test_lossless_readonly_audit(self):
        before = {p.name: p.read_bytes() for p in self.root.glob('*.csv')}
        import_raw(self.root, self.db)
        digest = hashlib.sha256(self.db.read_bytes()).hexdigest()
        report = audit(self.db)
        self.assertEqual(report['status'], 'success')
        self.assertFalse(report['semantic_mapping_validated'])
        self.assertEqual(report['row_counts']['order_payments'], 2)
        self.assertEqual(report['row_counts']['order_items'], 1)
        self.assertEqual(report['approval_range'][0], '2018-02-01T08:00:00')
        self.assertEqual(digest, hashlib.sha256(self.db.read_bytes()).hexdigest())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob('*.csv')})

    def test_missing_item_blocks_without_dropping_order(self):
        self.write('orders', ['order_id', 'customer_id', 'order_approved_at'],
                   [['o1','c1','2018/2/1 8:00'], ['o2','c1','2018/2/2 8:00']])
        import_raw(self.root, self.db)
        report = audit(self.db)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['checks']['approved_without_items'], 1)
        self.assertEqual(report['row_counts']['orders'], 2)

    def test_duplicate_rejected_and_database_cleaned(self):
        self.write('order_items', ['order_id', 'order_item_id'], [['o1','1'], ['o1','1']])
        with self.assertRaises(sqlite3.IntegrityError):
            import_raw(self.root, self.db)
        self.assertFalse(self.db.exists())

    def test_existing_database_is_never_overwritten(self):
        self.db.write_bytes(b'existing user file')
        with self.assertRaises(FileExistsError):
            import_raw(self.root, self.db)
        self.assertEqual(self.db.read_bytes(), b'existing user file')


if __name__ == '__main__':
    unittest.main()
