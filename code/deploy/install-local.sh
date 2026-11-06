#!/usr/bin/env bash
set -eu
project=/home/lego/lego-studio
install -d -m 755 /var/www/lego-studio
cp -r "$project/code/frontend/dist/." /var/www/lego-studio/
if [ ! -e /etc/lego-studio.env ]; then
    password=$(openssl rand -hex 24)
    mysql -e "CREATE USER 'lego_app'@'localhost' IDENTIFIED BY '$password'; GRANT SELECT, INSERT, UPDATE, DELETE ON lego_studio.* TO 'lego_app'@'localhost';"
    umask 077
    printf 'DATABASE_URL=mysql+pymysql://lego_app:%s@127.0.0.1:3306/lego_studio?charset=utf8mb4\n' "$password" > /etc/lego-studio.env
fi
install -m 644 "$project/code/deploy/lego-studio.service" /etc/systemd/system/lego-studio.service
install -m 644 "$project/code/deploy/nginx.conf" /etc/nginx/sites-available/lego-studio
ln -sfn /etc/nginx/sites-available/lego-studio /etc/nginx/sites-enabled/lego-studio
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now mysql lego-studio nginx
systemctl reload nginx
