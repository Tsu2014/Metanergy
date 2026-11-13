"""连接配置：从 .env 文件或环境变量读取。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_HOST = "192.168.30.220"
DEFAULT_PORT = 1433
DEFAULT_USER = "sa"
DEFAULT_DATABASE = "master"


@dataclass(frozen=True)
class SqlServerConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    user: str = DEFAULT_USER
    password: str = ""
    database: str = DEFAULT_DATABASE
    login_timeout: int = 5
    query_timeout: int = 30

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "SqlServerConfig":
        """优先读取环境变量；env_file 存在时先加载其中的 SQLSERVER_* 变量。"""
        if env_file:
            load_dotenv(env_file)
        return cls(
            host=os.getenv("SQLSERVER_HOST", DEFAULT_HOST),
            port=int(os.getenv("SQLSERVER_PORT", str(DEFAULT_PORT))),
            user=os.getenv("SQLSERVER_USER", DEFAULT_USER),
            password=os.getenv("SQLSERVER_PASSWORD", ""),
            database=os.getenv("SQLSERVER_DATABASE", DEFAULT_DATABASE),
            login_timeout=int(os.getenv("SQLSERVER_LOGIN_TIMEOUT", "5")),
            query_timeout=int(os.getenv("SQLSERVER_QUERY_TIMEOUT", "30")),
        )
