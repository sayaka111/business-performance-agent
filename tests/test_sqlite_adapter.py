import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from contextlib import closing

from business_performance_agent.config.settings import Settings
from business_performance_agent.tools.knowledge_loader import KnowledgeLoader
from business_performance_agent.tools.sqlite_query_tool import SQLiteQueryTool
from business_performance_agent.data_contract.sqlite_adapter import SQLiteDatasetAdapter
from business_performance_agent.models.schemas import BoundaryError
from business_performance_agent.runtime.engine import Runtime
from business_performance_agent.workflows.definition import load_workflow
from business_performance_agent.llm.client import MockLLMClient


class SQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.db'
        self.settings = Settings(logs=Path(self.temp.name) / 'logs')
        self.knowledge = KnowledgeLoader(self.settings.business / 'knowledge')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE orders(order_id TEXT, customer_id TEXT, order_approved_at TEXT, order_status TEXT)')
            db.execute('CREATE TABLE order_items(order_id TEXT, order_item_id TEXT, product_id TEXT, price TEXT)')
            db.execute('CREATE TABLE customers(customer_id TEXT, customer_unique_id TEXT)')
            db.execute('CREATE TABLE products(product_id TEXT, product_category_name TEXT)')
            db.execute("INSERT INTO products VALUES ('p','home')")
            for day, count in [('2017/1/1 0:00',1), ('2018/5/2 10:00',10), ('2018/6/2 10:00',7), ('2019/1/1 0:00',1)]:
                for n in range(count):
                    oid = day + str(n)
                    db.execute('INSERT INTO orders VALUES (?,?,?,?)', (oid,oid,day,'delivered'))
                    db.execute('INSERT INTO customers VALUES (?,?)', (oid,oid))
                    db.execute('INSERT INTO order_items VALUES (?,?,?,?)', (oid,'1','p','100.00'))
        self.adapter = SQLiteDatasetAdapter(self.knowledge, self.path)
        self.current = {'start':'2018-06-01','end':'2018-06-30'}
        self.baseline = {'start':'2018-05-01','end':'2018-05-31'}
        self.input = dict(metric_id='gross_gmv',current_period=self.current,baseline_period=self.baseline,filters={})

    def test_knowledge_aggregates_and_unavailable_semantics(self):
        for metric, expected in [('gross_gmv',700),('orders',7),('buyers',7),('units',7),('aov',100)]:
            self.assertEqual(self.adapter.metric(metric,self.current,{}), expected)
        self.assertFalse(self.adapter.metric_available('new_buyers'))
        self.assertFalse(self.adapter.dimension_available('region'))
        self.assertFalse(self.adapter.dimension_available('customer_type'))
        self.assertEqual(self.adapter.segments('gross_gmv','category',self.current,{}), {'home':700})
        self.assertIsNone(self.adapter.metric('aov',{'start':'2018-07-01','end':'2018-07-31'},{}))

    def test_readonly_and_policy(self):
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        for sql in ['DELETE FROM orders', 'WITH x AS (SELECT 1) DELETE FROM orders', 'SELECT load_extension(\'evil\')', 'SELECT * FROM sqlite_master']:
            with self.assertRaises(BoundaryError): self.adapter._select(sql)
        self.adapter.policy = replace(self.adapter.policy, max_rows=1)
        with self.assertRaises(BoundaryError): self.adapter.metric('gross_gmv',self.current,{})
        self.adapter.policy = replace(self.adapter.policy, query_timeout=0)
        with self.assertRaises(BoundaryError): self.adapter._select('SELECT COUNT(*) FROM orders')
        self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_scope_quality_and_missing_unattributable_date(self):
        scope = dict(metrics=['gross_gmv'],current_period=self.current,baseline_period=self.baseline,filters={})
        self.assertFalse(any(i['severity']=='blocked' for i in self.adapter.quality(scope)['issues']))
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO orders VALUES ('bad','bad',NULL,'delivered')")
            db.execute("INSERT INTO order_items VALUES ('bad','1','p','20')")
        with self.assertRaises(BoundaryError): self.adapter.metric('orders',self.current,{})
        self.adapter = SQLiteDatasetAdapter(self.knowledge, self.path)
        self.assertTrue(any(i['type']=='unattributable_payment_dates' for i in self.adapter.quality(scope)['issues']))

    def test_workflow_fixture_not_real_olist(self):
        runtime = Runtime(self.knowledge, SQLiteQueryTool(self.adapter),load_workflow(self.settings.workflow),self.settings,MockLLMClient())
        output = runtime.run(self.input)
        self.assertEqual(output['result']['workflow_status'],'completed')
        skills = {x['skill'] for x in runtime.trace['skills_called']}
        self.assertEqual(len(skills),7)
        self.assertEqual(runtime.trace['data_source']['backend'],'SQLite')
        self.assertTrue(runtime.trace['query_operations'])

    def test_missing_items_are_checked_in_requested_period(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO orders VALUES ('missing','x','2017/6/1 0:00','canceled')")
        self.adapter = SQLiteDatasetAdapter(self.knowledge,self.path)
        scope = dict(metrics=['gross_gmv'],current_period=self.current,baseline_period=self.baseline,filters={})
        self.assertFalse(any(x['severity']=='blocked' for x in self.adapter.quality(scope)['issues']))
        scope['current_period'] = {'start':'2017-06-01','end':'2017-06-30'}
        self.assertTrue(any(x['type']=='missing_required_values' for x in self.adapter.quality(scope)['issues']))

    def test_column_allowlist_and_unknown_preservation(self):
        self.adapter.policy = replace(self.adapter.policy,column_allowlist=())
        with self.assertRaises(BoundaryError): self.adapter.metric('orders',self.current,{})
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE products SET product_category_name=NULL')
        self.adapter = SQLiteDatasetAdapter(self.knowledge,self.path)
        self.assertEqual(self.adapter.segments('gross_gmv','category',self.current,{}),{'unknown':700})

    def test_injection_is_bound_as_filter_value(self):
        self.assertEqual(self.adapter.metric('orders',self.current,{'category': "home' OR 1=1 --"}),0)
        self.assertEqual(self.adapter.metric('orders',self.current,{}),7)


if __name__ == '__main__': unittest.main()
