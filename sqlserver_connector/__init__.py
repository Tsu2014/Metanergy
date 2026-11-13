"""SQL Server 连接器：基于 pymssql 的轻量级封装。"""

from .config import SqlServerConfig
from .connector import SqlServerConnector

__all__ = ["SqlServerConfig", "SqlServerConnector"]
__version__ = "0.1.0"
