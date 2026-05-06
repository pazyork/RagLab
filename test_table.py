#!/usr/bin/env python3
import nicegui
from nicegui import ui

print("NiceGUI version:", nicegui.__version__)
print("ui.table exists:", hasattr(ui, 'table'))
print("ui.table type:", type(ui.table) if hasattr(ui, 'table') else "N/A")
import inspect
print("ui.table signature:", inspect.signature(ui.table) if hasattr(ui, 'table') else "N/A")

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
    print("Table created successfully!")
except Exception as e:
    print(f"Error creating table: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
