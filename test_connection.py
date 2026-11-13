#!/usr/bin/env python3
"""连通性冒烟测试：python test_connection.py

在能访问目标服务器的机器上运行；退出码 0 表示连接成功，1 表示失败。
"""

import sys

from sqlserver_connector import SqlServerConfig, SqlServerConnector


def main() -> int:
    cfg = SqlServerConfig.from_env()
    print(f"目标服务器: {cfg.host}:{cfg.port}  用户: {cfg.user}  数据库: {cfg.database}")
    try:
        with SqlServerConnector(cfg) as db:
            info = db.query_one(
                "SELECT @@VERSION AS version, DB_NAME() AS db, SUSER_NAME() AS login"
            )
            print(f"连接成功，当前登录: {info['login']}，当前数据库: {info['db']}")
            print(f"服务器版本: {info['version'].splitlines()[0]}")

            dbs = db.query("SELECT name FROM sys.databases ORDER BY name")
            print(f"可见数据库（{len(dbs)} 个）: {', '.join(d['name'] for d in dbs)}")
    except Exception as exc:
        print(f"连接失败: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
