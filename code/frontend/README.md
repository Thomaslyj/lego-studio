# 前端

Vue 3 + Vite + Element Plus，中文 LEGO 风格工作台。开场动画使用 Three.js + cannon-es，所有零件模型都由程序生成，不依赖外部模型文件。

## 运行

```bash
npm install
npm run dev      # http://localhost:5173，/api 代理到 http://127.0.0.1:8000
npm run build    # 输出到 dist/
```

后端启动方式见 `docs/notes/backend.md`。如果后端不在本机 8000 端口，可以复制 `.env.example` 为 `.env`，并设置 `VITE_API_BASE`。部署时也可以让 Web 服务器把 `/api` 反向代理到后端。路由使用 hash 模式，静态部署不需要配置回退规则。

## 结构

- `src/intro/`：开场倾倒动画（`IntroScene.vue`）和零件模型（`pieces.js`）
- `src/views/`：套装探索、套装详情与备料、组装任务（列表/详情）、库存与入库、单据记录
- `src/components/`：套装图片（加载失败时显示色块占位）、颜色小砖、状态标签、备料明细表
- `src/api/`：接口封装；`lookup.js` 为单据明细补充零件名称和颜色
- `src/styles/lego.css`：设计变量、积木按钮、凸点底纹、Element Plus 主题覆盖

## 说明

- 套装图片按 `https://cdn.rebrickable.com/media/sets/{set_num}.jpg` 加载，离线或缺图时显示按主题着色的凸点占位，业务功能不受影响。
- 任务、入库单、领料单接口返回完整数组，前端负责状态筛选和分页。
- 入库单和领料单明细只返回零件编号和颜色编号。领料单借用对应任务的需求明细补全名称；入库单按零件编号查询库存目录补全名称。
