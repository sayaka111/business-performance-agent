from abc import ABC, abstractmethod


class SchemaTool(ABC):
    @abstractmethod
    def list_tables(self): ...
    @abstractmethod
    def get_table_schema(self, table): ...
    @abstractmethod
    def validate_field(self, table, field): ...


class MockSchemaTool(SchemaTool):
    def __init__(self, adapter):
        self.adapter = adapter

    def list_tables(self):
        return list(self.adapter.schema())

    def get_table_schema(self, table):
        return list(self.adapter.schema()[table])

    def validate_field(self, table, field):
        return field in self.adapter.schema().get(table, [])
