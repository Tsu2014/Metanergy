# metanergy

SQL Server 连接器（Python，基于 pymssql）。

默认连接配置：

- 服务器：`192.168.30.1`，端口 `1433`
- 账号：`sa`，密码通过 `.env` 中的 `SQLSERVER_PASSWORD` 配置
- 默认数据库：`master`

## 安装

```bash
pip install -r requirements.txt
cp .env.example .env   # 然后编辑 .env 填入密码等配置
```

`.env` 已被 `.gitignore` 忽略，凭据不会入库。所有配置项：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SQLSERVER_HOST` | `192.168.30.1` | 服务器地址 |
| `SQLSERVER_PORT` | `1433` | 端口 |
| `SQLSERVER_USER` | `sa` | 登录账号 |
| `SQLSERVER_PASSWORD` | （空） | 登录密码 |
| `SQLSERVER_DATABASE` | `master` | 默认数据库 |
| `SQLSERVER_LOGIN_TIMEOUT` | `5` | 登录超时（秒） |
| `SQLSERVER_QUERY_TIMEOUT` | `30` | 查询超时（秒） |

## 快速开始

```python
from sqlserver_connector import SqlServerConnector

with SqlServerConnector() as db:
    # 查询（返回字典列表，参数用 %(name)s 占位符防注入）
    rows = db.query("SELECT * FROM users WHERE id = %(id)s", {"id": 1})
    one = db.query_one("SELECT TOP 1 * FROM users")
    cnt = db.scalar("SELECT COUNT(*) AS c FROM users")

    # 写入（自动提交）
    db.execute("UPDATE users SET name = %(n)s WHERE id = %(id)s", {"n": "张三", "id": 1})

    # 批量写入
    db.execute_many(
        "INSERT INTO users (id, name) VALUES (%(id)s, %(name)s)",
        [{"id": 2, "name": "李四"}, {"id": 3, "name": "王五"}],
    )

    # 事务：要么全部提交，要么全部回滚
    with db.transaction():
        db.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
        db.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
```

也可以在代码里直接覆盖配置：

```python
from sqlserver_connector import SqlServerConfig, SqlServerConnector

cfg = SqlServerConfig(host="192.168.30.1", port=1433, user="sa",
                      password="...", database="mydb")
db = SqlServerConnector(cfg)
# 或：SqlServerConnector(database="mydb")，其余取 .env / 环境变量
```

## 验证连通性

在能访问目标服务器的机器上运行：

```bash
python test_connection.py
```

输出服务器版本、当前登录和可见数据库列表；退出码 0 表示成功。

## 测试

```bash
pip install -r requirements-dev.txt
pytest                                   # 单元测试（mock 驱动，无需真实服务器）
SQLSERVER_LIVE_TEST=1 pytest tests/test_live.py   # 真实连接集成测试
```
