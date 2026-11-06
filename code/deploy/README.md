# WSL Ubuntu 部署

适用于 Ubuntu 24.04、发行版内用户 `lego`；在该用户的 `/home/lego/lego-studio` 拉取本仓库。MySQL 8、nginx、Python 3 和 Git 需已安装，systemd 已启用。

1. 在 Windows 使用 mysqldump 导出原业务库，在 Linux 新建空的 `lego_studio` 数据库并恢复备份；备份不在仓库内。恢复前确认目标数据库为空，避免覆盖已有业务数据。
2. 在项目根目录创建 `.venv`，依次安装 `code/backend/requirements.txt` 和 `code/deploy/requirements-linux.txt`；后者支持 MySQL 8 的 `caching_sha2_password` 认证。
3. 在 Windows 源码目录执行 `npm ci`、`npm run build`，将 `code/frontend/dist` 复制到 Linux 项目对应目录；也可在 Linux 安装适配 Vite 的 Node.js 后构建。
4. 以 root 执行 `bash /home/lego/lego-studio/code/deploy/install-local.sh`。首次运行创建 `lego_app` 本机数据库账户并生成 `/etc/lego-studio.env`（仅 root 可读），配置并启动 systemd 和 nginx；后续运行保留已有账户与环境文件。
5. Windows 通过 `wsl -d Ubuntu-24.04 -- hostname -I` 获取 Linux 地址，再在浏览器访问 `http://<Linux-IP>/`。地址可能在 WSL 重启后改变。数据库及 API 只监听 Linux 本机，由 nginx 转发 API。

可以通过 `wsl -d Ubuntu-24.04 -u root -- systemctl status lego-studio nginx mysql` 查看服务。不要把环境文件、数据库凭据、备份或本机虚拟环境提交到仓库。若数据库不存在，必须先恢复再执行安装脚本。
