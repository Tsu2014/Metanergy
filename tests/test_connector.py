"""连接器单元测试：mock pymssql，验证连接、查询、事务行为。"""

import os
from unittest import mock

import pytest

from sqlserver_connector import SqlServerConfig, SqlServerConnector


@pytest.fixture()
def config():
    return SqlServerConfig(host="db.example.com", port=1433, user="sa",
                           password="secret", database="master")


@pytest.fixture()
def mock_pymssql():
    with mock.patch("sqlserver_connector.connector.pymssql") as m:
        yield m


def make_connector(mock_pymssql, config):
    conn = mock_pymssql.connect.return_value
    db = SqlServerConnector(config)
    return db, conn


class TestConfig:
    def test_defaults(self):
        cfg = SqlServerConfig()
        assert (cfg.host, cfg.port, cfg.user) == ("192.168.30.1", 1433, "sa")
        assert cfg.database == "master"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("SQLSERVER_HOST", "10.0.0.8")
        monkeypatch.setenv("SQLSERVER_PORT", "11433")
        monkeypatch.setenv("SQLSERVER_PASSWORD", "p@ss")
        cfg = SqlServerConfig.from_env(env_file=None)
        assert (cfg.host, cfg.port, cfg.password) == ("10.0.0.8", 11433, "p@ss")

    def test_from_dotenv_file(self, tmp_path):
        env = tmp_path / "test.env"
        env.write_text("SQLSERVER_HOST=192.168.30.1\nSQLSERVER_PASSWORD=test.888\n")
        old = os.environ.pop("SQLSERVER_PASSWORD", None)
        try:
            cfg = SqlServerConfig.from_env(str(env))
        finally:
            if old is not None:
                os.environ["SQLSERVER_PASSWORD"] = old
        assert cfg.password == "test.888"


class TestConnect:
    def test_connect_params(self, mock_pymssql, config):
        db = SqlServerConnector(config)
        db.connect()
        mock_pymssql.connect.assert_called_once_with(
            server="db.example.com", port="1433", user="sa", password="secret",
            database="master", login_timeout=5, timeout=30, as_dict=True,
        )

    def test_connect_is_idempotent(self, mock_pymssql, config):
        db = SqlServerConnector(config)
        db.connect()
        db.connect()
        assert mock_pymssql.connect.call_count == 1

    def test_context_manager_closes(self, mock_pymssql, config):
        with SqlServerConnector(config):
            pass
        mock_pymssql.connect.return_value.close.assert_called_once()


class TestQuery:
    def test_query_returns_dicts(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]

        rows = db.query("SELECT id FROM t WHERE x = %(x)s", {"x": 9})

        cursor.execute.assert_called_once_with("SELECT id FROM t WHERE x = %(x)s", {"x": 9})
        assert rows == [{"id": 1}, {"id": 2}]
        cursor.close.assert_called_once()

    def test_query_one_none_when_empty(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        conn.cursor.return_value.fetchone.return_value = None
        assert db.query_one("SELECT 1") is None

    def test_scalar(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        conn.cursor.return_value.fetchone.return_value = {"cnt": 42}
        assert db.scalar("SELECT COUNT(*) AS cnt FROM t") == 42


class TestExecute:
    def test_execute_commits_on_success(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        conn.cursor.return_value.rowcount = 3

        assert db.execute("UPDATE t SET x = 1") == 3
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    def test_execute_rolls_back_on_error(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        conn.cursor.return_value.execute.side_effect = RuntimeError("deadlock")

        with pytest.raises(RuntimeError):
            db.execute("UPDATE t SET x = 1")
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_execute_many(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        cursor = conn.cursor.return_value
        cursor.rowcount = 2
        n = db.execute_many("INSERT INTO t VALUES (%(a)s)", [{"a": 1}, {"a": 2}])
        assert n == 2
        cursor.executemany.assert_called_once()
        conn.commit.assert_called_once()


class TestTransaction:
    def test_commit_when_no_error(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        with db.transaction():
            db.execute("UPDATE a")
            db.execute("UPDATE b")
        # 事务内不自动提交，退出时统一提交一次
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    def test_rollback_on_error(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        with pytest.raises(ValueError), db.transaction():
            db.execute("UPDATE a")
            raise ValueError("boom")
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_no_nested_transactions(self, mock_pymssql, config):
        db, _ = make_connector(mock_pymssql, config)
        with db.transaction(), pytest.raises(RuntimeError):
            with db.transaction():
                pass


class TestPing:
    def test_ping_true(self, mock_pymssql, config):
        db, conn = make_connector(mock_pymssql, config)
        conn.cursor.return_value.fetchone.return_value = {"one": 1}
        assert db.ping() is True

    def test_ping_false_on_error(self, mock_pymssql, config):
        mock_pymssql.connect.side_effect = OSError("unreachable")
        db = SqlServerConnector(config)
        assert db.ping() is False
