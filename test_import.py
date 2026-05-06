#!/usr/bin/env python3
from nicegui import ui

# Test importing modules
print("Importing i18n...")
from raglab.i18n import t
print("Importing evaluate...")
from raglab.ui.pages.evaluate import render_evaluate
print("Importing chunk_lab...")
from raglab.ui.pages.chunk_lab import render_chunk_lab
print("Importing settings...")
from raglab.ui.pages.settings import render_settings

print("All imports done!")
print("ui.table still exists:", hasattr(ui, 'table'))
import inspect
print("ui.table signature after imports:", inspect.signature(ui.table))

# Test create table
try:
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id'},
        {'name': 'name', 'label': 'Name', 'field': 'name'},
    ]
    rows = [
        {'id': 1, 'name': 'Test 1'},
        {'id': 2, 'name': 'Test 2'},
    ]
    table = ui.table(columns=columns, rows=rows, row_key='id')
    print("Table created successfully after imports!")
except Exception as e:
    print(f"Error creating table after imports: {type(e).__name__}: {e}")
