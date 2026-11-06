"""Import the fixed public snapshot and reproducible simulated opening stock.

Run from the project root after creating an empty lego_studio database.
"""
import csv
import io
import sys
import zipfile
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'code' / 'backend'))
from app.db import engine


def rows(archive, name):
    with archive.open(name + '.csv') as source:
        return list(csv.DictReader(io.TextIOWrapper(source, encoding='utf-8-sig', newline='')))


def insert(conn, table, fields, values):
    sql = text('INSERT INTO ' + table + ' (' + ','.join(fields) + ') VALUES (' + ','.join(':' + f for f in fields) + ')')
    for offset in range(0, len(values), 3000):
        conn.execute(sql, values[offset:offset + 3000])


def main():
    with zipfile.ZipFile(ROOT / 'data/raw/lego-database.zip') as archive, engine.begin() as conn:
        schema_name = conn.execute(text('SELECT DATABASE()')).scalar()
        if not schema_name:
            raise RuntimeError('请在 DATABASE_URL 中指定已创建的空数据库')
        table_count = conn.execute(text('''SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema=:schema_name'''), {'schema_name': schema_name}).scalar()
        if table_count:
            raise RuntimeError('目标数据库不是空库，已停止导入')
        ddl = (ROOT / 'data/sql/schema-workbench.sql').read_text(encoding='utf-8')
        if '`lego_studio`' not in ddl:
            raise RuntimeError('Workbench 脚本中缺少预期的数据库名，请先核对脚本')
        ddl = ddl.replace('`lego_studio`', conn.dialect.identifier_preparer.quote_identifier(schema_name))
        for statement in ddl.split(';'):
            if statement.strip():
                conn.exec_driver_sql(statement)
        themes = rows(archive, 'themes')
        insert(conn, 'themes', ['id', 'name'], themes)
        conn.execute(text('UPDATE themes SET parent_id=:parent_id WHERE id=:id'), [r for r in themes if r['parent_id']])
        catalog = {}
        for table, fields in [('part_categories', ['id','name']), ('colors', ['id','name','rgb','is_trans']), ('parts', ['part_num','name','part_cat_id']), ('sets', ['set_num','name','year','theme_id','num_parts'])]:
            data = rows(archive, table)
            catalog[table] = data
            if table == 'colors':
                for r in data:
                    r['is_trans'] = r['is_trans'] == 't'
            insert(conn, table, fields, data)
        nested = {int(r['inventory_id']) for r in rows(archive, 'inventory_sets')}
        inventories = rows(archive, 'inventories')
        parts = rows(archive, 'inventory_parts')
        part_ids = {r['part_num'] for r in catalog['parts']}
        color_ids = {r['id'] for r in catalog['colors']}
        inventory_ids = {r['id'] for r in inventories}
        invalid = [r for r in parts if r['part_num'] not in part_ids or r['color_id'] not in color_ids or r['inventory_id'] not in inventory_ids]
        incomplete = {int(r['inventory_id']) for r in invalid}
        for r in inventories:
            r['supported'] = int(r['id']) not in nested | incomplete
        insert(conn, 'inventories', ['id','version','set_num','supported'], inventories)
        parts = [r for r in parts if r['part_num'] in part_ids and r['color_id'] in color_ids and r['inventory_id'] in inventory_ids]
        for r in parts:
            r['is_spare'] = r['is_spare'] == 't'
        insert(conn, 'inventory_parts', ['inventory_id','part_num','color_id','quantity','is_spare'], parts)
        # Deterministic mix of empty, low and well-stocked items. This is simulated data.
        conn.execute(text("""INSERT INTO stock(part_num,color_id,opening_quantity,quantity)
            SELECT part_num,color_id, MOD(CRC32(CONCAT(part_num, '-', color_id, '-20261105')), 101),
                   MOD(CRC32(CONCAT(part_num, '-', color_id, '-20261105')), 101)
            FROM inventory_parts GROUP BY part_num,color_id"""))
        for table in ['themes','part_categories','colors','parts','sets','inventories','inventory_parts','stock']:
            print(table, conn.execute(text('SELECT COUNT(*) FROM ' + table)).scalar())
        print('nested inventory versions excluded from ordering:', len(nested))
        print('invalid composition rows excluded:', len(invalid), 'affected inventory versions:', len(incomplete))


if __name__ == '__main__':
    main()
