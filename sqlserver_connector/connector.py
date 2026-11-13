"""SqlServerConnector：连接管理、查询与事务。"""

from __future__ import annotations

import dataclasses
import logging
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence

import pymssql

from .config import SqlServerConfig

logger = logging.getLogger(__name__)

Params = Mapping[str, Any] | Sequence[Any] | None


class SqlServerConnector:
    """SQL Server 连接器。

    用法::

        from sqlserver_connector import SqlServerConnector

        with SqlServerConnector() as db:
            rows = db.query("SELECT * FROM users WHERE id = %(id)s", {"id": 1})
    """

    def __init__(self, config: SqlServerConfig | None = None, **overrides: Any):
        if config is None:
            config = SqlServerConfig.from_env()
        if overrides:
            config = dataclasses.replace(config, **overrides)
        self.config = config
        self._conn: Any = None
        self._in_transaction = False

    def connect(self) -> Any:
        """建立连接（幂等：已连接时直接复用）。"""
        if self._conn is not None:
            return self._conn
        cfg = self.config
        logger.info(
            "连接 SQL Server %s:%s（用户 %s，数据库 %s）",
            cfg.host, cfg.port, cfg.user, cfg.database,
        )
        self._conn = pymssql.connect(
            server=cfg.host,
            port=str(cfg.port),
            user=cfg.user,
            password=cfg.password,
            database=cfg.database,
            login_timeout=cfg.login_timeout,
            timeout=cfg.query_timeout,
            as_dict=True,
        )
        return self._conn

    @property
    def connection(self) -> Any:
        return self.connect()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None
                logger.info("连接已关闭")

    def __enter__(self) -> "SqlServerConnector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    # ---------- 查询 ----------

    def query(self, sql: str, params: Params = None) -> list[dict[str, Any]]:
        """执行查询，返回字典列表。参数用 %(name)s 命名占位符或 %s 位置占位符。"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def query_one(self, sql: str, params: Params = None) -> dict[str, Any] | None:
        """执行查询，返回第一行（无结果时返回 None）。"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def scalar(self, sql: str, params: Params = None) -> Any:
        """执行查询，返回第一行第一列的值。"""
        row = self.query_one(sql, params)
        if row is None:
            return None
        return next(iter(row.values()))

    # ---------- 写入 ----------

    def execute(self, sql: str, params: Params = None) -> int:
        """执行 INSERT/UPDATE/DELETE/DDL，返回受影响行数。

        非事务模式下自动提交，失败自动回滚；事务模式下由 transaction() 统一提交。
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            rowcount = cursor.rowcount
        except Exception:
            if not self._in_transaction:
                self.connection.rollback()
            raise
        else:
            if not self._in_transaction:
                self.connection.commit()
            return rowcount
        finally:
            cursor.close()

    def execute_many(self, sql: str, seq_of_params: Sequence[Params]) -> int:
        """批量执行（executemany），返回受影响行数。"""
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, seq_of_params)
            rowcount = cursor.rowcount
        except Exception:
            if not self._in_transaction:
                self.connection.rollback()
            raise
        else:
            if not self._in_transaction:
                self.connection.commit()
            return rowcount
        finally:
            cursor.close()

    @contextmanager
    def transaction(self) -> Iterator["SqlServerConnector"]:
        """事务上下文：块内所有 execute 要么一起提交，要么一起回滚。

        with db.transaction():
            db.execute("UPDATE ...")
            db.execute("INSERT ...")
        """
        if self._in_transaction:
            raise RuntimeError("不支持嵌套事务")
        self._in_transaction = True
        try:
            yield self
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
        finally:
            self._in_transaction = False

    # ---------- 健康检查 ----------

    def ping(self) -> bool:
        """SELECT 1 探活，返回是否连通。"""
        try:
            return self.scalar("SELECT 1 AS one") == 1
        except Exception:
            logger.exception("ping 失败")
            return False
