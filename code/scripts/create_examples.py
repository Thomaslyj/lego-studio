"""Create reproducible simulated business examples in a freshly imported database."""
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.db import engine
from app.main import Item, ReceiptInput, TaskInput, create_receipt, create_task, confirm_receipt, issue, set_detail

with engine.connect() as conn:
    if conn.execute(text('SELECT COUNT(*) FROM tasks')).scalar() or conn.execute(text('SELECT COUNT(*) FROM receipts')).scalar():
        raise SystemExit('业务单据已存在，未创建示例。请只在刚导入的空业务数据中运行。')
    set_num = conn.execute(text('''SELECT i.set_num FROM inventories i
        WHERE i.supported=1 AND i.id=(SELECT j.id FROM inventories j WHERE j.set_num=i.set_num ORDER BY j.version DESC,j.id DESC LIMIT 1)
        AND EXISTS(SELECT 1 FROM inventory_parts p WHERE p.inventory_id=i.id AND p.is_spare=0)
        ORDER BY i.set_num LIMIT 1''')).scalar_one()

items = set_detail(set_num, 1)['items']
receipt = create_receipt(ReceiptInput(items=[Item(part_num=i['part_num'],color_id=i['color_id'],quantity=int(i['required_quantity'])+10) for i in items]))
confirm_receipt(receipt['id'])
task = create_task(TaskInput(set_num=set_num,quantity=1))
issue(task['id'])
draft = create_task(TaskInput(set_num=set_num,quantity=2))
print('已创建模拟示例：套装',set_num,'入库单',receipt['id'],'已领料任务',task['id'],'草稿任务',draft['id'])
