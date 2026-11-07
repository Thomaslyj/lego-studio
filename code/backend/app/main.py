from collections import defaultdict
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from .db import engine

app = FastAPI(title='LEGO 拼搭工作室备料与库存管理')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['*'], allow_headers=['*'])
PositiveInt = Annotated[int, Field(strict=True, gt=0)]


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail': '输入不合法，请检查字段、数量及分页参数'})


class TaskInput(BaseModel):
    set_num: str
    quantity: PositiveInt
    inventory_id: PositiveInt | None = None


class Item(BaseModel):
    part_num: str
    color_id: int
    quantity: PositiveInt


class ReceiptInput(BaseModel):
    items: list[Item] = Field(min_length=1)


def row(conn, sql, params=None):
    result = conn.execute(text(sql), params or {}).mappings().first()
    return dict(result) if result else None


def all_rows(conn, sql, params=None):
    return [dict(r) for r in conn.execute(text(sql), params or {}).mappings()]


def required(conn, sql, params=None):
    result = row(conn, sql, params)
    if result is None:
        raise HTTPException(404, '记录不存在')
    return result


def version(conn, set_num, inventory_id=None, require_parts=False):
    if inventory_id is None:
        result = required(conn, '''SELECT id,version,supported FROM inventories
            WHERE set_num=:set_num ORDER BY version DESC,id DESC LIMIT 1''', {'set_num': set_num})
    else:
        result = required(conn, 'SELECT id,version,supported FROM inventories WHERE set_num=:set_num AND id=:id', {'set_num':set_num, 'id':inventory_id})
    if not result['supported']:
        raise HTTPException(409, '该清单包含嵌套套装或数据不完整，暂不支持')
    if require_parts and not conn.execute(text('''SELECT EXISTS(
        SELECT 1 FROM inventory_parts WHERE inventory_id=:id AND is_spare=0)'''), {'id': result['id']}).scalar():
        raise HTTPException(409, '该清单没有可领用的零件，不能创建或修改拼搭任务')
    return result


def needs(conn, inventory_id, quantity):
    return all_rows(conn, '''SELECT ip.part_num,p.name AS part_name,ip.color_id,c.name AS color_name,
        c.rgb,SUM(ip.quantity)*:quantity AS required_quantity,COALESCE(s.quantity,0) AS stock_quantity,
        GREATEST(SUM(ip.quantity)*:quantity-COALESCE(s.quantity,0),0) AS shortage
        FROM inventory_parts ip JOIN parts p ON p.part_num=ip.part_num JOIN colors c ON c.id=ip.color_id
        LEFT JOIN stock s ON s.part_num=ip.part_num AND s.color_id=ip.color_id
        WHERE ip.inventory_id=:inventory_id AND ip.is_spare=0
        GROUP BY ip.part_num,p.name,ip.color_id,c.name,c.rgb,s.quantity ORDER BY ip.part_num,ip.color_id''',
        {'inventory_id': inventory_id, 'quantity': quantity})


@app.get('/api/themes')
def themes():
    with engine.connect() as conn:
        return all_rows(conn, 'SELECT * FROM themes ORDER BY name')


@app.get('/api/sets')
def sets(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str = '', theme_id: int | None = None, year: int | None = None, min_parts: int = Query(0, ge=0)):
    params = {'search': '%' + search + '%', 'theme_id': theme_id, 'year': year, 'min_parts': min_parts, 'limit': page_size, 'offset': (page-1)*page_size}
    where = ' WHERE s.name LIKE :search AND (:theme_id IS NULL OR s.theme_id=:theme_id) AND (:year IS NULL OR s.year=:year) AND s.num_parts>=:min_parts'
    with engine.connect() as conn:
        total = conn.execute(text('SELECT COUNT(*) FROM sets s' + where), params).scalar()
        items = all_rows(conn, 'SELECT s.*,t.name AS theme_name FROM sets s JOIN themes t ON t.id=s.theme_id' + where + ' ORDER BY s.set_num LIMIT :limit OFFSET :offset', params)
    return {'total': total, 'page': page, 'items': items}


@app.get('/api/sets/{set_num}/versions')
def set_versions(set_num: str):
    with engine.connect() as conn:
        required(conn, 'SELECT set_num FROM sets WHERE set_num=:set_num', {'set_num':set_num})
        return all_rows(conn, '''SELECT i.id,i.version,
            (i.supported AND EXISTS (SELECT 1 FROM inventory_parts p
                WHERE p.inventory_id=i.id AND p.is_spare=0)) AS supported
            FROM inventories i WHERE i.set_num=:set_num ORDER BY i.version DESC,i.id DESC''', {'set_num':set_num})


@app.get('/api/sets/{set_num}')
def set_detail(set_num: str, quantity: int = Query(1, ge=1), inventory_id: int | None = None):
    with engine.connect() as conn:
        s = required(conn, 'SELECT * FROM sets WHERE set_num=:set_num', {'set_num': set_num})
        v = version(conn, set_num, inventory_id)
        return {'set': s, 'inventory': v, 'quantity': quantity, 'items': needs(conn, v['id'], quantity)}


@app.get('/api/stock')
def stock(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str = ''):
    params = {'search': '%'+search+'%', 'limit':page_size, 'offset':(page-1)*page_size}
    with engine.connect() as conn:
        if not search:
            return {'items': all_rows(conn, '''SELECT s.part_num,p.name,s.color_id,c.name AS color_name,c.rgb,s.quantity
                FROM stock s JOIN parts p ON p.part_num=s.part_num JOIN colors c ON c.id=s.color_id
                ORDER BY s.part_num,s.color_id LIMIT :limit OFFSET :offset''', params),
                'total': conn.execute(text('SELECT COUNT(*) FROM stock')).scalar()}
        return {'items': all_rows(conn, '''SELECT s.part_num,p.name,s.color_id,c.name AS color_name,c.rgb,s.quantity
            FROM stock s JOIN parts p ON p.part_num=s.part_num JOIN colors c ON c.id=s.color_id
            WHERE p.name LIKE :search OR p.part_num LIKE :search ORDER BY s.part_num,s.color_id LIMIT :limit OFFSET :offset''', params),
            'total': conn.execute(text('SELECT COUNT(*) FROM stock s JOIN parts p ON p.part_num=s.part_num WHERE p.name LIKE :search OR p.part_num LIKE :search'), params).scalar()}


@app.get('/api/tasks')
def tasks():
    with engine.connect() as conn:
        return all_rows(conn, '''SELECT t.*,i.set_num,s.name AS set_name FROM tasks t JOIN inventories i ON i.id=t.inventory_id JOIN sets s ON s.set_num=i.set_num ORDER BY t.id DESC''')


@app.post('/api/tasks', status_code=201)
def create_task(body: TaskInput):
    with engine.begin() as conn:
        v = version(conn, body.set_num, body.inventory_id, require_parts=True)
        result = conn.execute(text('INSERT INTO tasks(inventory_id,quantity) VALUES(:inventory_id,:quantity)'), {'inventory_id':v['id'], 'quantity':body.quantity})
        return {'id': result.lastrowid, 'status':'draft'}


@app.get('/api/tasks/{task_id}')
def task_detail(task_id: int):
    with engine.connect() as conn:
        task = required(conn, 'SELECT t.*,i.set_num FROM tasks t JOIN inventories i ON i.id=t.inventory_id WHERE t.id=:id', {'id':task_id})
        return {'task':task, 'items':needs(conn,task['inventory_id'],task['quantity'])}


@app.put('/api/tasks/{task_id}')
def update_task(task_id: int, body: TaskInput):
    with engine.begin() as conn:
        task = required(conn, '''SELECT t.*,i.set_num FROM tasks t JOIN inventories i ON i.id=t.inventory_id
            WHERE t.id=:id FOR UPDATE''', {'id':task_id})
        if task['status'] != 'draft': raise HTTPException(409, '已领料任务不可修改')
        selected_id = body.inventory_id
        if selected_id is None and body.set_num == task['set_num']:
            selected_id = task['inventory_id']
        v = version(conn, body.set_num, selected_id, require_parts=True)
        conn.execute(text('UPDATE tasks SET inventory_id=:inventory_id,quantity=:quantity WHERE id=:id'), {'inventory_id':v['id'], 'quantity':body.quantity, 'id':task_id})
    return {'id': task_id, 'status':'draft'}


@app.delete('/api/tasks/{task_id}')
def delete_task(task_id: int):
    with engine.begin() as conn:
        task = required(conn, 'SELECT * FROM tasks WHERE id=:id FOR UPDATE', {'id':task_id})
        if task['status'] != 'draft': raise HTTPException(409, '已领料任务不可删除')
        conn.execute(text('DELETE FROM tasks WHERE id=:id'), {'id':task_id})
    return {'deleted':task_id}


def save_items(conn, receipt_id, items):
    merged = defaultdict(int)
    for item in items: merged[(item.part_num, item.color_id)] += item.quantity
    for (part_num, color_id), quantity in sorted(merged.items()):
        required(conn, 'SELECT part_num FROM stock WHERE part_num=:part_num AND color_id=:color_id', {'part_num':part_num,'color_id':color_id})
        conn.execute(text('INSERT INTO receipt_items(receipt_id,part_num,color_id,quantity) VALUES(:id,:part_num,:color_id,:quantity)'), {'id':receipt_id,'part_num':part_num,'color_id':color_id,'quantity':quantity})


@app.get('/api/receipts')
def receipts():
    with engine.connect() as conn: return all_rows(conn, 'SELECT * FROM receipts ORDER BY id DESC')


@app.post('/api/receipts', status_code=201)
def create_receipt(body: ReceiptInput):
    with engine.begin() as conn:
        result = conn.execute(text('INSERT INTO receipts() VALUES()'))
        save_items(conn, result.lastrowid, body.items)
        return {'id':result.lastrowid, 'status':'draft'}


@app.get('/api/receipts/{receipt_id}')
def receipt_detail(receipt_id: int):
    with engine.connect() as conn:
        return {'receipt':required(conn,'SELECT * FROM receipts WHERE id=:id',{'id':receipt_id}), 'items':all_rows(conn,'SELECT * FROM receipt_items WHERE receipt_id=:id',{'id':receipt_id})}


@app.put('/api/receipts/{receipt_id}')
def update_receipt(receipt_id: int, body: ReceiptInput):
    with engine.begin() as conn:
        receipt = required(conn,'SELECT * FROM receipts WHERE id=:id FOR UPDATE',{'id':receipt_id})
        if receipt['status'] != 'draft': raise HTTPException(409, '已入库单不可修改')
        conn.execute(text('DELETE FROM receipt_items WHERE receipt_id=:id'), {'id':receipt_id})
        save_items(conn, receipt_id, body.items)
    return {'id':receipt_id,'status':'draft'}


@app.delete('/api/receipts/{receipt_id}')
def delete_receipt(receipt_id: int):
    with engine.begin() as conn:
        receipt = required(conn,'SELECT * FROM receipts WHERE id=:id FOR UPDATE',{'id':receipt_id})
        if receipt['status'] != 'draft': raise HTTPException(409, '已入库单不可删除')
        conn.execute(text('DELETE FROM receipts WHERE id=:id'), {'id':receipt_id})
    return {'deleted':receipt_id}


@app.post('/api/receipts/{receipt_id}/confirm')
def confirm_receipt(receipt_id: int):
    with engine.begin() as conn:
        receipt = required(conn,'SELECT * FROM receipts WHERE id=:id FOR UPDATE',{'id':receipt_id})
        if receipt['status'] == 'posted': return {'id':receipt_id,'status':'posted'}
        items = all_rows(conn,'SELECT * FROM receipt_items WHERE receipt_id=:id ORDER BY part_num,color_id',{'id':receipt_id})
        for item in items:
            conn.execute(text('UPDATE stock SET quantity=quantity+:quantity WHERE part_num=:part_num AND color_id=:color_id'), item)
        conn.execute(text("UPDATE receipts SET status='posted' WHERE id=:id"), {'id':receipt_id})
    return {'id':receipt_id,'status':'posted'}


@app.post('/api/tasks/{task_id}/issue')
def issue(task_id: int):
    with engine.begin() as conn:
        task = required(conn,'SELECT * FROM tasks WHERE id=:id FOR UPDATE',{'id':task_id})
        if task['status'] == 'issued':
            return required(conn,'SELECT * FROM issues WHERE task_id=:id',{'id':task_id})
        items = needs(conn,task['inventory_id'],task['quantity'])
        if not items: raise HTTPException(409, '该清单没有可领用的零件')
        for item in items:
            current = required(conn, 'SELECT quantity FROM stock WHERE part_num=:part_num AND color_id=:color_id FOR UPDATE', item)
            if current['quantity'] < item['required_quantity']:
                raise HTTPException(409, '库存不足，领料未执行')
        issue_id = conn.execute(text('INSERT INTO issues(task_id) VALUES(:id)'),{'id':task_id}).lastrowid
        for item in items:
            item['issue_id'] = issue_id
            conn.execute(text('UPDATE stock SET quantity=quantity-:required_quantity WHERE part_num=:part_num AND color_id=:color_id'), item)
            conn.execute(text('INSERT INTO issue_items(issue_id,part_num,color_id,quantity) VALUES(:issue_id,:part_num,:color_id,:required_quantity)'), item)
        conn.execute(text("UPDATE tasks SET status='issued' WHERE id=:id"), {'id':task_id})
        return {'id':issue_id, 'task_id':task_id}


@app.get('/api/issues')
def issues():
    with engine.connect() as conn: return all_rows(conn,'SELECT * FROM issues ORDER BY id DESC')


@app.get('/api/issues/{issue_id}')
def issue_detail(issue_id: int):
    with engine.connect() as conn:
        return {'issue':required(conn,'SELECT * FROM issues WHERE id=:id',{'id':issue_id}), 'items':all_rows(conn,'SELECT * FROM issue_items WHERE issue_id=:id',{'id':issue_id})}
