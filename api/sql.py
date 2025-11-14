import os
from typing import Any, Iterable, List, Optional, Tuple

from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

try:
    import psycopg2
    from psycopg2 import pool as _pool
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    _pool = None  # type: ignore


class DB:
    """PostgreSQL connection pool helpers.

    If env/driver is not available, `connection_pool` stays None and callers
    should handle it (return empty results or 503).
    """

    connection_pool: Optional["_pool.SimpleConnectionPool"] = None
    init_error: Optional[str] = None

    @classmethod
    def _init_pool(cls) -> None:
        if psycopg2 is None:
            cls.init_error = "psycopg2 not installed"
            return
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        dbname = os.getenv("DB_NAME")
        if not all([user, password, host, port, dbname]):
            cls.init_error = "Missing DB env vars (DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME)"
            return
        try:
            cls.connection_pool = _pool.SimpleConnectionPool(
                1, 10, user=user, password=password, host=host, port=port, dbname=dbname
            )
        except Exception as e:
            cls.connection_pool = None
            cls.init_error = str(e)

    @classmethod
    def connect(cls):
        if cls.connection_pool is None:
            raise RuntimeError("DB pool not initialized")
        return cls.connection_pool.getconn()

    @classmethod
    def release(cls, conn) -> None:
        if cls.connection_pool is None:
            return
        cls.connection_pool.putconn(conn)

    @classmethod
    def fetchall(cls, sql: str, params: Optional[Iterable[Any]] = None) -> List[Tuple]:
        conn = cls.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
        finally:
            cls.release(conn)

    @classmethod
    def fetchone(cls, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Tuple]:
        conn = cls.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        finally:
            cls.release(conn)

    @classmethod
    def execute(cls, sql: str, params: Optional[Iterable[Any]] = None) -> int:
        """Execute DML and commit. Returns affected row count."""
        conn = cls.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                affected = cur.rowcount
            conn.commit()
            return affected
        finally:
            cls.release(conn)


# Initialize pool on import
# DB._init_pool()


def table_has_column(table_name: str, column_name: str) -> bool:
    """Return True if given table has the specified column.
    Safe to call even if pool isn't ready (returns False).
    """
    if DB.connection_pool is None:
        return False
    try:
        row = DB.fetchone(
            'SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s LIMIT 1',
            (table_name, column_name),
        )
        return bool(row)
    except Exception:
        return False


def list_tasks() -> List[dict]:
    """Return tasks from DB: [{id, name}]"""
    if DB.connection_pool is None:
        return []
    rows = DB.fetchall('SELECT "TaskId", "TaskName" FROM "Task" ORDER BY "TaskId"')
    return [{"id": r[0], "name": r[1]} for r in rows]


def list_programs() -> List[dict]:
    """Return programs from DB: [{code, name, cat, userCount}]"""
    if DB.connection_pool is None:
        return []
    # Include usage count from EmployeeProgs; Category may not exist in schema (kept as empty string here)
    sql = (
        'SELECT p."ProgId", p."ProgName", COALESCE(c.cnt,0) AS "UserCount" '
        'FROM "Program" p '
        'LEFT JOIN (SELECT "ProgId", COUNT(*)::int AS cnt FROM "EmployeeProgs" GROUP BY "ProgId") c ON c."ProgId"=p."ProgId" '
        'ORDER BY p."ProgId"'
    )
    rows = DB.fetchall(sql)
    return [{"code": r[0], "name": r[1], "cat": "", "userCount": int(r[2] or 0)} for r in rows]


def list_task_program_codes(task_id: str) -> List[str]:
    if DB.connection_pool is None:
        return []
    rows = DB.fetchall('SELECT "ProgId" FROM "TaskProgs" WHERE "TaskId" = %s ORDER BY "ProgId"', (task_id,))
    return [r[0] for r in rows]


def list_programs_of_task(task_id: str) -> List[dict]:
    """Return detailed programs of a task by joining TaskProgs -> Program."""
    if DB.connection_pool is None:
        return []
    has_cat = table_has_column("Program", "Category")
    select_cat = 'COALESCE(p."Category",\'\')' if has_cat else "''"
    sql = f'SELECT p."ProgId", p."ProgName", {select_cat} FROM "TaskProgs" tp JOIN "Program" p ON p."ProgId"=tp."ProgId" WHERE tp."TaskId"=%s ORDER BY p."ProgId"'
    rows = DB.fetchall(sql, (task_id,))
    return [{"ProgId": r[0], "ProgName": r[1], "Category": r[2]} for r in rows]


def add_task_programs(task_id: str, prog_ids: List[str]) -> int:
    if DB.connection_pool is None:
        return 0
    total = 0
    for pid in (prog_ids or []):
        if not pid:
            continue
        a = DB.execute('INSERT INTO "TaskProgs" ("TaskId","ProgId") VALUES (%s,%s) ON CONFLICT ("TaskId","ProgId") DO NOTHING', (task_id, pid))
        total += max(0, a)
    return total


def delete_task_program(task_id: str, prog_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "TaskProgs" WHERE "TaskId"=%s AND "ProgId"=%s', (task_id, prog_id))


def search_units(unit_id: Optional[str] = None,
                 unit_name: Optional[str] = None,
                 manager: Optional[str] = None) -> List[dict]:
    """Search Unit table with manager name.
    Returns: [{UnitId, UnitName, ManagerName, WorkIntroduce}]
    If DB is not available, returns empty list.
    """
    if DB.connection_pool is None:
        return []

    sql = [
        'SELECT u."UnitId", u."UnitName", COALESCE(e."EmployeeName",\'\') AS "ManagerName", COALESCE(u."WorkIntroduce",\'\') AS "WorkIntroduce"',
        'FROM "Unit" u',
        'LEFT JOIN "Employee" e ON e."EmployeeId" = u."ManagerUser"',
        'WHERE 1=1',
    ]
    params: List[Any] = []
    if unit_id:
        sql.append('AND u."UnitId" ILIKE %s')
        params.append(f"%{unit_id}%")
    if unit_name:
        sql.append('AND u."UnitName" ILIKE %s')
        params.append(f"%{unit_name}%")
    if manager:
        # allow search by manager employee id or name
        sql.append('AND (u."ManagerUser" ILIKE %s OR e."EmployeeName" ILIKE %s)')
        params.append(f"%{manager}%")
        params.append(f"%{manager}%")
    sql.append('ORDER BY u."UnitId"')
    rows = DB.fetchall("\n".join(sql), tuple(params) if params else None)
    return [
        {"UnitId": r[0], "UnitName": r[1], "ManagerName": r[2], "WorkIntroduce": r[3]}
        for r in rows
    ]


def list_units(limit: int = 50, offset: int = 0) -> List[dict]:
    if DB.connection_pool is None:
        return []
    sql = 'SELECT u."UnitId", u."UnitName", COALESCE(e."EmployeeName",\'\') AS "ManagerName", COALESCE(u."WorkIntroduce",\'\') FROM "Unit" u LEFT JOIN "Employee" e ON e."EmployeeId" = u."ManagerUser" ORDER BY u."UnitId" LIMIT %s OFFSET %s'
    rows = DB.fetchall(sql, (limit, offset))
    return [
        {"UnitId": r[0], "UnitName": r[1], "ManagerName": r[2], "WorkIntroduce": r[3]}
        for r in rows
    ]


def db_info() -> dict:
    if DB.connection_pool is None:
        return {"connected": False, "error": "connection not initialized"}
    info = {"connected": True}
    try:
        db = DB.fetchone("SELECT current_database()")
        usr = DB.fetchone("SELECT current_user")
        sp = DB.fetchone("SHOW search_path")
        info.update({
            "database": db[0] if db else None,
            "user": usr[0] if usr else None,
            "search_path": sp[0] if sp else None,
        })
    except Exception as e:
        info.update({"error": str(e)})
    return info


def get_unit_exact(unit_id: str) -> Optional[dict]:
    if DB.connection_pool is None:
        return None
    row = DB.fetchone('SELECT "UnitId", "UnitName", COALESCE("ManagerUser",\'\'), COALESCE("WorkIntroduce",\'\') FROM "Unit" WHERE "UnitId" = %s', (unit_id,))
    if not row:
        return None
    return {"UnitId": row[0], "UnitName": row[1], "ManagerUser": row[2], "WorkIntroduce": row[3]}


def employee_exists(emp_id: str) -> bool:
    if DB.connection_pool is None:
        return False
    row = DB.fetchone('SELECT 1 FROM "Employee" WHERE "EmployeeId" = %s LIMIT 1', (emp_id,))
    return bool(row)


def update_unit(unit_id: str, unit_name: str, manager_user: Optional[str], introduce: Optional[str]) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('UPDATE "Unit" SET "UnitName"=%s, "ManagerUser"=%s, "WorkIntroduce"=%s WHERE "UnitId"=%s',
                      (unit_name, manager_user if manager_user else None, introduce if introduce else None, unit_id))


def insert_unit(unit_id: str, unit_name: str, manager_user: Optional[str], introduce: Optional[str]) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('INSERT INTO "Unit" ("UnitId","UnitName","ManagerUser","WorkIntroduce") VALUES (%s,%s,%s,%s)',
                      (unit_id, unit_name, manager_user if manager_user else None, introduce if introduce else None))


def unit_in_use(unit_id: str) -> bool:
    """Check if the unit is referenced by employees (or other tables if needed)."""
    if DB.connection_pool is None:
        return False
    row = DB.fetchone('SELECT 1 FROM "Employee" WHERE "UnitId"=%s LIMIT 1', (unit_id,))
    return bool(row)


def delete_unit(unit_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "Unit" WHERE "UnitId"=%s', (unit_id,))


# Role helpers
def get_role_exact(role_id: str) -> Optional[dict]:
    if DB.connection_pool is None:
        return None
    row = DB.fetchone('SELECT "RoleId","RoleName","VisibleMark" FROM "Role" WHERE "RoleId"=%s', (role_id,))
    if not row:
        return None
    return {"RoleId": row[0], "RoleName": row[1], "VisibleMark": bool(row[2])}


def insert_role(role_id: str, role_name: str, visible: bool) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('INSERT INTO "Role" ("RoleId","RoleName","VisibleMark") VALUES (%s,%s,%s)', (role_id, role_name, visible))


def update_role(role_id: str, role_name: str, visible: bool) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('UPDATE "Role" SET "RoleName"=%s, "VisibleMark"=%s WHERE "RoleId"=%s', (role_name, visible, role_id))


def delete_role(role_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "Role" WHERE "RoleId"=%s', (role_id,))


# Employee CRUD/search
def search_employees(emp_id: Optional[str] = None,
                     emp_name: Optional[str] = None,
                     unit_id: Optional[str] = None,
                     role_id: Optional[str] = None) -> List[dict]:
    if DB.connection_pool is None:
        return []
    sql = [
        'SELECT "EmployeeId", "EmployeeName", "UnitId", COALESCE("JobName",\'\'), "RoleId" FROM "Employee"',
        'WHERE 1=1'
    ]
    params: List[Any] = []
    if emp_id:
        sql.append('AND "EmployeeId" ILIKE %s')
        params.append(f"%{emp_id}%")
    if emp_name:
        sql.append('AND "EmployeeName" ILIKE %s')
        params.append(f"%{emp_name}%")
    if unit_id:
        sql.append('AND "UnitId" ILIKE %s')
        params.append(f"%{unit_id}%")
    if role_id:
        sql.append('AND "RoleId" ILIKE %s')
        params.append(f"%{role_id}%")
    sql.append('ORDER BY "EmployeeId"')
    rows = DB.fetchall("\n".join(sql), tuple(params) if params else None)
    return [{"EmployeeId": r[0], "EmployeeName": r[1], "UnitId": r[2], "JobName": r[3], "RoleId": r[4]} for r in rows]


def get_employee_exact(emp_id: str) -> Optional[dict]:
    if DB.connection_pool is None:
        return None
    r = DB.fetchone('SELECT "EmployeeId","EmployeeName","UnitId",COALESCE("JobName",\'\'),"RoleId" FROM "Employee" WHERE "EmployeeId"=%s', (emp_id,))
    if not r:
        return None
    return {"EmployeeId": r[0], "EmployeeName": r[1], "UnitId": r[2], "JobName": r[3], "RoleId": r[4]}


def insert_employee(emp_id: str, name: str, unit_id: str, job: Optional[str], role_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('INSERT INTO "Employee" ("EmployeeId","EmployeeName","UnitId","JobName","RoleId") VALUES (%s,%s,%s,%s,%s)', (emp_id, name, unit_id, job if job else None, role_id))


def update_employee(emp_id: str, name: str, unit_id: str, job: Optional[str], role_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('UPDATE "Employee" SET "EmployeeName"=%s, "UnitId"=%s, "JobName"=%s, "RoleId"=%s WHERE "EmployeeId"=%s', (name, unit_id, job if job else None, role_id, emp_id))


def employee_has_progs(emp_id: str) -> bool:
    if DB.connection_pool is None:
        return False
    r = DB.fetchone('SELECT 1 FROM "EmployeeProgs" WHERE "EmployeeId"=%s LIMIT 1', (emp_id,))
    return bool(r)


def delete_employee(emp_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "Employee" WHERE "EmployeeId"=%s', (emp_id,))


# Task CRUD/search
def search_tasks(task_id: Optional[str] = None, task_name: Optional[str] = None) -> List[dict]:
    if DB.connection_pool is None:
        return []
    sql = ['SELECT "TaskId","TaskName" FROM "Task" WHERE 1=1']
    params: List[Any] = []
    if task_id:
        sql.append('AND "TaskId" ILIKE %s')
        params.append(f"%{task_id}%")
    if task_name:
        sql.append('AND "TaskName" ILIKE %s')
        params.append(f"%{task_name}%")
    sql.append('ORDER BY "TaskId"')
    rows = DB.fetchall("\n".join(sql), tuple(params) if params else None)
    return [{"TaskId": r[0], "TaskName": r[1]} for r in rows]


def get_task_exact(task_id: str) -> Optional[dict]:
    if DB.connection_pool is None:
        return None
    r = DB.fetchone('SELECT "TaskId","TaskName" FROM "Task" WHERE "TaskId"=%s', (task_id,))
    if not r:
        return None
    return {"TaskId": r[0], "TaskName": r[1]}


def insert_task(task_id: str, task_name: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('INSERT INTO "Task" ("TaskId","TaskName") VALUES (%s,%s)', (task_id, task_name))


def update_task(task_id: str, task_name: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('UPDATE "Task" SET "TaskName"=%s WHERE "TaskId"=%s', (task_name, task_id))


def task_in_use(task_id: str) -> bool:
    if DB.connection_pool is None:
        return False
    r = DB.fetchone('SELECT 1 FROM "TaskProgs" WHERE "TaskId"=%s LIMIT 1', (task_id,))
    if r:
        return True
    r = DB.fetchone('SELECT 1 FROM "RoleTasks" WHERE "TaskId"=%s LIMIT 1', (task_id,))
    return bool(r)


def delete_task(task_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "Task" WHERE "TaskId"=%s', (task_id,))


# Program CRUD/search
def search_programs(prog_id: Optional[str] = None,
                    prog_name: Optional[str] = None,
                    category: Optional[str] = None) -> List[dict]:
    if DB.connection_pool is None:
        return []
    # Some DBs may not have Category column (see ERP.sql). Detect and adapt.
    has_cat = table_has_column("Program", "Category")
    select_cat = 'COALESCE(p."Category",\'\')' if has_cat else "''"
    sql_parts = [
        'SELECT p."ProgId", p."ProgName", ' + select_cat + ', COALESCE(c.cnt,0) AS "UserCount"',
        'FROM "Program" p',
        'LEFT JOIN (SELECT "ProgId", COUNT(*)::int AS cnt FROM "EmployeeProgs" GROUP BY "ProgId") c ON c."ProgId"=p."ProgId"',
        'WHERE 1=1'
    ]
    params: List[Any] = []
    if prog_id:
        sql_parts.append('AND p."ProgId" ILIKE %s')
        params.append(f"%{prog_id}%")
    if prog_name:
        sql_parts.append('AND p."ProgName" ILIKE %s')
        params.append(f"%{prog_name}%")
    if category and has_cat:
        sql_parts.append('AND COALESCE(p."Category",\'\') ILIKE %s')
        params.append(f"%{category}%")
    sql_parts.append('ORDER BY p."ProgId"')
    rows = DB.fetchall("\n".join(sql_parts), tuple(params) if params else None)
    return [
        {"ProgId": r[0], "ProgName": r[1], "Category": r[2], "UserCount": int(r[3] or 0)}
        for r in rows
    ]


def get_program_exact(prog_id: str) -> Optional[dict]:
    if DB.connection_pool is None:
        return None
    has_cat = table_has_column("Program", "Category")
    select_cat = 'COALESCE("Category",\'\')' if has_cat else "''"
    r = DB.fetchone(f'SELECT "ProgId","ProgName", {select_cat} FROM "Program" WHERE "ProgId"=%s', (prog_id,))
    if not r:
        return None
    return {"ProgId": r[0], "ProgName": r[1], "Category": r[2]}


def insert_program(prog_id: str, prog_name: str, category: Optional[str]) -> int:
    if DB.connection_pool is None:
        return 0
    if table_has_column("Program", "Category"):
        return DB.execute('INSERT INTO "Program" ("ProgId","ProgName","Category") VALUES (%s,%s,%s)', (prog_id, prog_name, category if category else None))
    # Fallback schema without Category column
    return DB.execute('INSERT INTO "Program" ("ProgId","ProgName") VALUES (%s,%s)', (prog_id, prog_name))


def update_program(prog_id: str, prog_name: str, category: Optional[str]) -> int:
    if DB.connection_pool is None:
        return 0
    if table_has_column("Program", "Category"):
        return DB.execute('UPDATE "Program" SET "ProgName"=%s, "Category"=%s WHERE "ProgId"=%s', (prog_name, category if category else None, prog_id))
    # Fallback schema without Category column
    return DB.execute('UPDATE "Program" SET "ProgName"=%s WHERE "ProgId"=%s', (prog_name, prog_id))


def program_in_use(prog_id: str) -> bool:
    if DB.connection_pool is None:
        return False
    r = DB.fetchone('SELECT 1 FROM "TaskProgs" WHERE "ProgId"=%s LIMIT 1', (prog_id,))
    if r:
        return True
    r = DB.fetchone('SELECT 1 FROM "EmployeeProgs" WHERE "ProgId"=%s LIMIT 1', (prog_id,))
    return bool(r)


def delete_program(prog_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "Program" WHERE "ProgId"=%s', (prog_id,))


def search_roles(role_id: Optional[str] = None,
                 role_name: Optional[str] = None,
                 visible: Optional[str] = None) -> List[dict]:
    """Search Role table. Returns [{RoleId, RoleName, VisibleMark}]."""
    if DB.connection_pool is None:
        return []
    sql = [
        'SELECT "RoleId", "RoleName", "VisibleMark" FROM "Role"',
        'WHERE 1=1'
    ]
    params: List[Any] = []
    if role_id:
        sql.append('AND "RoleId" ILIKE %s')
        params.append(f"%{role_id}%")
    if role_name:
        sql.append('AND "RoleName" ILIKE %s')
        params.append(f"%{role_name}%")
    if visible is not None and str(visible) != "":
        v = str(visible).lower() in ("1", "true", "t", "yes", "y", "是")
        sql.append('AND "VisibleMark" = %s')
        params.append(v)
    sql.append('ORDER BY "RoleId"')
    rows = DB.fetchall("\n".join(sql), tuple(params) if params else None)
    return [
        {"RoleId": r[0], "RoleName": r[1], "VisibleMark": bool(r[2])}
        for r in rows
    ]


# Employee → Programs
def list_programs_of_employee(employee_id: str) -> List[dict]:
    """Return programs accessible by an employee from EmployeeProgs join Program.
    Returns: [{ProgId, ProgName, Category}]
    Category may be empty string when column is not present.
    """
    if DB.connection_pool is None:
        return []
    has_cat = table_has_column("Program", "Category")
    select_cat = 'COALESCE(p."Category",\'\')' if has_cat else "''"
    sql = f'SELECT p."ProgId", p."ProgName", {select_cat} FROM "EmployeeProgs" ep JOIN "Program" p ON p."ProgId"=ep."ProgId" WHERE ep."EmployeeId"=%s ORDER BY p."ProgId"'
    rows = DB.fetchall(sql, (employee_id,))
    return [{"ProgId": r[0], "ProgName": r[1], "Category": r[2]} for r in rows]


def add_employee_programs(employee_id: str, prog_ids: List[str]) -> int:
    if DB.connection_pool is None:
        return 0
    total = 0
    for pid in (prog_ids or []):
        if not pid:
            continue
        a = DB.execute('INSERT INTO "EmployeeProgs" ("EmployeeId","ProgId") VALUES (%s,%s) ON CONFLICT ("EmployeeId","ProgId") DO NOTHING', (employee_id, pid))
        total += max(0, a)
    return total


def delete_employee_program(employee_id: str, prog_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "EmployeeProgs" WHERE "EmployeeId"=%s AND "ProgId"=%s', (employee_id, prog_id))


# Role → Programs (via RoleTasks -> TaskProgs -> Program)
def list_programs_of_role(role_id: str) -> List[dict]:
    if DB.connection_pool is None:
        return []
    has_cat = table_has_column("Program", "Category")
    select_cat = 'COALESCE(p."Category",\'\')' if has_cat else "''"
    sql = (
        'SELECT DISTINCT p."ProgId", p."ProgName", ' + select_cat +
        ' FROM "RoleTasks" rt'
        ' JOIN "TaskProgs" tp ON tp."TaskId" = rt."TaskId"'
        ' JOIN "Program" p ON p."ProgId" = tp."ProgId"'
        ' WHERE rt."RoleId" = %s'
        ' ORDER BY p."ProgId"'
    )
    rows = DB.fetchall(sql, (role_id,))
    return [{"ProgId": r[0], "ProgName": r[1], "Category": r[2]} for r in rows]


# Role ↔ Tasks
def list_tasks_of_role(role_id: str) -> List[dict]:
    if DB.connection_pool is None:
        return []
    sql = (
        'SELECT t."TaskId", t."TaskName" '
        'FROM "RoleTasks" rt JOIN "Task" t ON t."TaskId" = rt."TaskId" '
        'WHERE rt."RoleId"=%s ORDER BY t."TaskId"'
    )
    rows = DB.fetchall(sql, (role_id,))
    return [{"TaskId": r[0], "TaskName": r[1]} for r in rows]


def add_role_tasks(role_id: str, task_ids: List[str]) -> int:
    if DB.connection_pool is None:
        return 0
    affected_total = 0
    for tid in (task_ids or []):
        if not tid:
            continue
        a = DB.execute('INSERT INTO "RoleTasks" ("RoleId","TaskId") VALUES (%s,%s) ON CONFLICT ("RoleId","TaskId") DO NOTHING', (role_id, tid))
        affected_total += max(0, a)
    return affected_total


def delete_role_task(role_id: str, task_id: str) -> int:
    if DB.connection_pool is None:
        return 0
    return DB.execute('DELETE FROM "RoleTasks" WHERE "RoleId"=%s AND "TaskId"=%s', (role_id, task_id))


# Program → Employees
def list_employees_of_program(prog_id: str) -> List[dict]:
    """Return employees who have this program in EmployeeProgs.
    Returns: [{EmployeeId, EmployeeName, UnitId, UnitName, RoleId, RoleName}]
    """
    if DB.connection_pool is None:
        return []
    sql = (
        'SELECT e."EmployeeId", e."EmployeeName", e."UnitId", COALESCE(u."UnitName",\'\') AS "UnitName", '
        'e."RoleId", COALESCE(r."RoleName",\'\') AS "RoleName" '
        'FROM "EmployeeProgs" ep '
        'JOIN "Employee" e ON e."EmployeeId" = ep."EmployeeId" '
        'LEFT JOIN "Unit" u ON u."UnitId" = e."UnitId" '
        'LEFT JOIN "Role" r ON r."RoleId" = e."RoleId" '
        'WHERE ep."ProgId" = %s '
        'ORDER BY e."EmployeeId"'
    )
    rows = DB.fetchall(sql, (prog_id,))
    return [
        {
            "EmployeeId": r[0],
            "EmployeeName": r[1],
            "UnitId": r[2],
            "UnitName": r[3],
            "RoleId": r[4],
            "RoleName": r[5],
        }
        for r in rows
    ]
