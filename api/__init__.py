from flask import Blueprint
from .sql import DB  # 匯入你的 DB 類別

bp = Blueprint('api', __name__)

@bp.before_app_request
def ensure_db_pool():
    if DB.connection_pool is None:
        print("初始化 PostgreSQL Connection Pool ...")
        DB._init_pool()

from . import api  # noqa: E402,F401

