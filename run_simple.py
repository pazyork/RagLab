#!/usr/bin/env python3
from nicegui import ui

@ui.page("/")
def index():
    ui.label("Hello World")
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id'},
        {'name': 'name', 'label': 'Name', 'field': 'name'},
    ]
    rows = [
        {'id': 1, 'name': 'Test 1'},
        {'id': 2, 'name': 'Test 2'},
    ]
    ui.table(columns=columns, rows=rows, row_key='id')

ui.run(port=8080, reload=False)
