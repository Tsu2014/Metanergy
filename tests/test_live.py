"""真实连接集成测试：默认跳过。

在能访问目标 SQL Server 的机器上启用：

    SQLSERVER_LIVE_TEST=1 pytest tests/test_live.py
"""

import os

import pytest

from sqlserver_connector import SqlServerConnector

pytestmark = pytest.mark.skipif(
    os.getenv("SQLSERVER_LIVE_TEST") != "1",
    reason="需要真实 SQL Server 环境，设 SQLSERVER_LIVE_TEST=1 启用",
)


def test_live_ping_and_version():
    with SqlServerConnector() as db:
        assert db.ping() is True
        version = db.scalar("SELECT @@VERSION AS v")
        assert "Microsoft SQL Server" in version


def test_live_temp_table_roundtrip():
    with SqlServerConnector() as db:
        db.execute("CREATE TABLE #conn_test (id INT PRIMARY KEY, name NVARCHAR(20))")
        with db.transaction():
            db.execute_many(
                "INSERT INTO #conn_test (id, name) VALUES (%(id)s, %(name)s)",
                [{"id": 1, "name": "张"}, {"id": 2, "name": "李"}],
            )
        rows = db.query("SELECT id, name FROM #conn_test ORDER BY id")
        assert rows == [{"id": 1, "name": "张"}, {"id": 2, "name": "李"}]
