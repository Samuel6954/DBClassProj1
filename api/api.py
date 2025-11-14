from flask import jsonify, request

from . import bp
from .sql import (
    DB,
    list_programs,
    list_task_program_codes,
    list_tasks,
    search_units,
    list_units,
    db_info,
    get_unit_exact,
    employee_exists,
    update_unit,
    insert_unit,
    get_role_exact,
    insert_role,
    update_role,
    delete_role,
    search_roles,
    search_employees,
    get_employee_exact,
    insert_employee,
    update_employee,
    delete_employee,
    employee_has_progs,
    search_tasks,
    get_task_exact,
    insert_task,
    update_task,
    delete_task,
    task_in_use,
    search_programs,
    get_program_exact,
    insert_program,
    update_program,
    delete_program,
    program_in_use,
    list_programs_of_employee,
    list_programs_of_role,
    list_tasks_of_role,
    add_role_tasks,
    delete_role_task,
    list_programs_of_task,
    add_task_programs,
    delete_task_program,
    add_employee_programs,
    delete_employee_program,
    list_employees_of_program,
)


@bp.get("/tasks")
def api_tasks():
    if DB.connection_pool is None:
        return jsonify([])
    return jsonify(list_tasks())


@bp.get("/programs")
def api_programs():
    if DB.connection_pool is None:
        return jsonify([])
    # Optional filters
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    pname = (request.args.get("ProgName") or request.args.get("progName") or "").strip()
    cat = (request.args.get("Category") or request.args.get("category") or "").strip()
    if pid or pname or cat:
        return jsonify(search_programs(pid or None, pname or None, cat or None))
    return jsonify(list_programs())


@bp.get("/program/employees")
def api_program_employees():
    if DB.connection_pool is None:
        return jsonify([])
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    if not pid:
        return jsonify([])
    return jsonify(list_employees_of_program(pid))


@bp.get("/taskprogs")
def api_taskprogs():
    task_id = request.args.get("taskId") or ""
    if DB.connection_pool is None:
        return jsonify([])
    return jsonify(list_task_program_codes(task_id))


@bp.get("/task/programs")
def api_task_programs():
    if DB.connection_pool is None:
        return jsonify([])
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    if not tid:
        return jsonify([])
    return jsonify(list_programs_of_task(tid))


@bp.post("/task/programs")
def api_task_programs_add():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    tid = (p.get("TaskId") or p.get("taskId") or "").strip()
    items = p.get("ProgIds") or p.get("progIds") or p.get("ProgId") or []
    prog_ids = [items] if isinstance(items, str) else [str(x) for x in (items or []) if str(x).strip()]
    if not tid or not prog_ids:
        return jsonify({"ok": False, "error": "TaskId/ProgIds required"}), 400
    inserted = add_task_programs(tid, prog_ids)
    return jsonify({"ok": True, "inserted": inserted, "requested": len(prog_ids)})


@bp.delete("/task/programs")
def api_task_programs_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    if not tid or not pid:
        return jsonify({"ok": False, "error": "TaskId/ProgId required"}), 400
    a = delete_task_program(tid, pid)
    return jsonify({"ok": a > 0, "affected": a})


@bp.get("/units")
def api_units():
    unit_id = request.args.get("unitId") or request.args.get("UnitId") or ""
    unit_name = request.args.get("unitName") or request.args.get("UnitName") or ""
    manager = request.args.get("manager") or request.args.get("ManagerUser") or ""
    if DB.connection_pool is None:
        return jsonify([])
    data = search_units(unit_id.strip() or None, unit_name.strip() or None, manager.strip() or None)
    return jsonify(data)


@bp.get("/roles")
def api_roles():
    if DB.connection_pool is None:
        return jsonify([])
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    rname = (request.args.get("RoleName") or request.args.get("roleName") or "").strip()
    vis = request.args.get("VisibleMark") or request.args.get("visible")
    data = search_roles(rid or None, rname or None, vis)
    return jsonify(data)


@bp.get("/role")
def api_role_get():
    if DB.connection_pool is None:
        return jsonify({}), 503
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    if not rid:
        return jsonify({"error": "RoleId required"}), 400
    data = get_role_exact(rid)
    if not data:
        return jsonify({}), 404
    return jsonify(data)


@bp.post("/role")
def api_role_save():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    payload = request.get_json(silent=True) or {}
    rid = (payload.get("RoleId") or "").strip()
    rname = (payload.get("RoleName") or "").strip()
    vis = payload.get("VisibleMark")
    visible = bool(vis) if isinstance(vis, bool) else str(vis).lower() in ("1","true","t","yes","y","是")
    mode = (payload.get("mode") or "").strip().lower()  # 'insert' or 'update'
    if not rid or not rname:
        return jsonify({"error": "RoleId and RoleName required"}), 400
    exists = get_role_exact(rid) is not None
    # Strict create/update behavior to avoid confusion
    if mode == 'insert':
        if exists:
            return jsonify({"ok": False, "error": "代碼已存在，請更換 RoleId"}), 409
        affected = insert_role(rid, rname, visible)
        return jsonify({"ok": affected > 0, "affected": affected, "mode": "insert"})
    if mode == 'update':
        if not exists:
            return jsonify({"ok": False, "error": "代碼不存在，無法更新"}), 404
        affected = update_role(rid, rname, visible)
        return jsonify({"ok": affected > 0, "affected": affected, "mode": "update"})
    # Fallback: keep previous behavior when mode not specified (upsert)
    affected = update_role(rid, rname, visible) if exists else insert_role(rid, rname, visible)
    return jsonify({"ok": affected > 0, "affected": affected, "mode": "update" if exists else "insert"})


@bp.delete("/role")
def api_role_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    if not rid:
        return jsonify({"error": "RoleId required"}), 400
    try:
        affected = delete_role(rid)
        if affected <= 0:
            return jsonify({"ok": False, "affected": 0}), 404
        return jsonify({"ok": True, "affected": affected})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 409


@bp.get("/units/all")
def api_units_all():
    if DB.connection_pool is None:
        return jsonify([])
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except Exception:
        limit, offset = 50, 0
    return jsonify(list_units(limit=limit, offset=offset))


@bp.get("/db/health")
def api_db_health():
    # Minimal health check: try to run a simple query if pool exists
    ok = False
    err = None
    if DB.connection_pool is not None:
        try:
            from .sql import DB as _DB
            _ = _DB.fetchone("SELECT 1")
            ok = True
        except Exception as e:
            err = str(e)
    else:
        err = "connection not initialized"
    return jsonify({"connected": ok, "error": err})


@bp.get("/db/info")
def api_db_info():
    return jsonify(db_info())


@bp.get("/unit")
def api_unit_get():
    if DB.connection_pool is None:
        return jsonify({}), 503
    unit_id = (request.args.get("UnitId") or request.args.get("unitId") or "").strip()
    if not unit_id:
        return jsonify({"error": "UnitId required"}), 400
    data = get_unit_exact(unit_id)
    if not data:
        return jsonify({}), 404
    return jsonify(data)


@bp.get("/employees/exists")
def api_employee_exists():
    if DB.connection_pool is None:
        return jsonify({"exists": False}), 200
    emp_id = (request.args.get("EmployeeId") or request.args.get("employeeId") or "").strip()
    if not emp_id:
        return jsonify({"exists": False}), 200
    return jsonify({"exists": employee_exists(emp_id)})


@bp.post("/unit")
def api_unit_save():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    payload = request.get_json(silent=True) or {}
    unit_id = (payload.get("UnitId") or "").strip()
    unit_name = (payload.get("UnitName") or "").strip()
    manager = (payload.get("ManagerUser") or "").strip()
    intro = (payload.get("WorkIntroduce") or "").strip()
    mode = (payload.get("mode") or "").strip().lower()  # 'insert' | 'update'
    if not unit_id or not unit_name:
        return jsonify({"error": "UnitId and UnitName required"}), 400
    if manager:
        if not employee_exists(manager):
            return jsonify({"error": "主管工號不存在"}), 400
    exists = get_unit_exact(unit_id) is not None
    if mode == 'insert':
        if exists:
            return jsonify({"ok": False, "error": "代碼已存在，請更換 UnitId"}), 409
        affected = insert_unit(unit_id, unit_name, manager or None, intro or None)
        return jsonify({"ok": affected > 0, "affected": affected, "mode": "insert"})
    if mode == 'update':
        if not exists:
            return jsonify({"ok": False, "error": "代碼不存在，無法更新"}), 404
        affected = update_unit(unit_id, unit_name, manager or None, intro or None)
        return jsonify({"ok": affected > 0, "affected": affected, "mode": "update"})
    # fallback upsert (for backward compatibility)
    affected = update_unit(unit_id, unit_name, manager or None, intro or None) if exists else insert_unit(unit_id, unit_name, manager or None, intro or None)
    return jsonify({"ok": affected > 0, "affected": affected, "mode": "update" if exists else "insert"})


@bp.delete("/unit")
def api_unit_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    uid = (request.args.get("UnitId") or request.args.get("unitId") or "").strip()
    if not uid:
        return jsonify({"error": "UnitId required"}), 400
    if get_unit_exact(uid) is None:
        return jsonify({"ok": False, "error": "代碼不存在"}), 404
    # 若單位仍被員工參照則阻擋
    from .sql import unit_in_use, delete_unit
    if unit_in_use(uid):
        return jsonify({"ok": False, "error": "有員工使用此單位，無法刪除"}), 409
    try:
        affected = delete_unit(uid)
        if affected <= 0:
            return jsonify({"ok": False, "affected": 0}), 404
        return jsonify({"ok": True, "affected": affected})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 409


# Employees
@bp.get("/employees")
def api_employees():
    if DB.connection_pool is None:
        return jsonify([])
    eid = (request.args.get("EmployeeId") or request.args.get("EmpId") or request.args.get("employeeId") or "").strip()
    name = (request.args.get("EmployeeName") or request.args.get("EmpName") or request.args.get("employeeName") or "").strip()
    unit = (request.args.get("UnitId") or "").strip()
    role = (request.args.get("RoleId") or "").strip()
    return jsonify(search_employees(eid or None, name or None, unit or None, role or None))


@bp.get("/employee/programs")
def api_employee_programs():
    if DB.connection_pool is None:
        return jsonify([])
    eid = (request.args.get("EmployeeId") or request.args.get("employeeId") or "").strip()
    if not eid:
        return jsonify([])
    return jsonify(list_programs_of_employee(eid))


@bp.post("/employee/programs")
def api_employee_programs_add():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    eid = (p.get("EmployeeId") or p.get("employeeId") or "").strip()
    items = p.get("ProgIds") or p.get("progIds") or p.get("ProgId") or []
    prog_ids = [items] if isinstance(items, str) else [str(x) for x in (items or []) if str(x).strip()]
    if not eid or not prog_ids:
        return jsonify({"ok": False, "error": "EmployeeId/ProgIds required"}), 400
    inserted = add_employee_programs(eid, prog_ids)
    return jsonify({"ok": True, "inserted": inserted, "requested": len(prog_ids)})


@bp.delete("/employee/programs")
def api_employee_programs_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    eid = (request.args.get("EmployeeId") or request.args.get("employeeId") or "").strip()
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    if not eid or not pid:
        return jsonify({"ok": False, "error": "EmployeeId/ProgId required"}), 400
    a = delete_employee_program(eid, pid)
    return jsonify({"ok": a > 0, "affected": a})


@bp.get("/role/programs")
def api_role_programs():
    if DB.connection_pool is None:
        return jsonify([])
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    if not rid:
        return jsonify([])
    return jsonify(list_programs_of_role(rid))


@bp.get("/role/tasks")
def api_role_tasks():
    if DB.connection_pool is None:
        return jsonify([])
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    if not rid:
        return jsonify([])
    return jsonify(list_tasks_of_role(rid))


@bp.post("/role/tasks")
def api_role_tasks_add():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    rid = (p.get("RoleId") or p.get("roleId") or "").strip()
    items = p.get("TaskIds") or p.get("taskIds") or p.get("TaskId") or []
    if isinstance(items, str):
        task_ids = [items]
    else:
        task_ids = [str(x) for x in (items or []) if str(x).strip()]
    if not rid or not task_ids:
        return jsonify({"ok": False, "error": "RoleId/TaskIds required"}), 400
    inserted = add_role_tasks(rid, task_ids)
    return jsonify({"ok": True, "inserted": inserted, "requested": len(task_ids)})


@bp.delete("/role/tasks")
def api_role_tasks_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    rid = (request.args.get("RoleId") or request.args.get("roleId") or "").strip()
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    if not rid or not tid:
        return jsonify({"ok": False, "error": "RoleId/TaskId required"}), 400
    a = delete_role_task(rid, tid)
    return jsonify({"ok": a > 0, "affected": a})


@bp.get("/employee")
def api_employee_get():
    if DB.connection_pool is None:
        return jsonify({}), 503
    eid = (request.args.get("EmployeeId") or request.args.get("employeeId") or "").strip()
    if not eid:
        return jsonify({"error": "EmployeeId required"}), 400
    data = get_employee_exact(eid)
    if not data:
        return jsonify({}), 404
    return jsonify(data)


@bp.post("/employee")
def api_employee_save():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    eid = (p.get("EmployeeId") or "").strip()
    name = (p.get("EmployeeName") or "").strip()
    unit = (p.get("UnitId") or "").strip()
    job = (p.get("JobName") or "").strip()
    role = (p.get("RoleId") or "").strip()
    mode = (p.get("mode") or "").strip().lower()
    if not eid or not name or not unit or not role:
        return jsonify({"error": "EmployeeId/EmployeeName/UnitId/RoleId required"}), 400
    # dependencies
    if get_unit_exact(unit) is None:
        return jsonify({"error": "UnitId 不存在"}), 400
    if get_role_exact(role) is None:
        return jsonify({"error": "RoleId 不存在"}), 400
    exists = get_employee_exact(eid) is not None
    if mode == 'insert':
        if exists:
            return jsonify({"ok": False, "error": "代碼已存在，請更換 EmployeeId"}), 409
        a = insert_employee(eid, name, unit, job or None, role)
        return jsonify({"ok": a > 0, "affected": a, "mode": "insert"})
    if mode == 'update':
        if not exists:
            return jsonify({"ok": False, "error": "代碼不存在，無法更新"}), 404
        a = update_employee(eid, name, unit, job or None, role)
        return jsonify({"ok": a > 0, "affected": a, "mode": "update"})
    a = update_employee(eid, name, unit, job or None, role) if exists else insert_employee(eid, name, unit, job or None, role)
    return jsonify({"ok": a > 0, "affected": a, "mode": "update" if exists else "insert"})


@bp.delete("/employee")
def api_employee_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    eid = (request.args.get("EmployeeId") or request.args.get("employeeId") or "").strip()
    if not eid:
        return jsonify({"error": "EmployeeId required"}), 400
    if get_employee_exact(eid) is None:
        return jsonify({"ok": False, "error": "代碼不存在"}), 404
    if employee_has_progs(eid):
        return jsonify({"ok": False, "error": "此員工有程式關聯，無法刪除"}), 409
    a = delete_employee(eid)
    return jsonify({"ok": a > 0, "affected": a})


# Tasks
@bp.get("/tasks2")
def api_tasks_search():
    if DB.connection_pool is None:
        return jsonify([])
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    tname = (request.args.get("TaskName") or request.args.get("taskName") or "").strip()
    return jsonify(search_tasks(tid or None, tname or None))


@bp.get("/task")
def api_task_get():
    if DB.connection_pool is None:
        return jsonify({}), 503
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    if not tid:
        return jsonify({"error": "TaskId required"}), 400
    data = get_task_exact(tid)
    if not data:
        return jsonify({}), 404
    return jsonify(data)


@bp.post("/task")
def api_task_save():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    tid = (p.get("TaskId") or "").strip()
    tname = (p.get("TaskName") or "").strip()
    mode = (p.get("mode") or "").strip().lower()
    if not tid or not tname:
        return jsonify({"error": "TaskId and TaskName required"}), 400
    exists = get_task_exact(tid) is not None
    if mode == 'insert':
        if exists:
            return jsonify({"ok": False, "error": "代碼已存在，請更換 TaskId"}), 409
        a = insert_task(tid, tname)
        return jsonify({"ok": a > 0, "affected": a, "mode": "insert"})
    if mode == 'update':
        if not exists:
            return jsonify({"ok": False, "error": "代碼不存在，無法更新"}), 404
        a = update_task(tid, tname)
        return jsonify({"ok": a > 0, "affected": a, "mode": "update"})
    a = update_task(tid, tname) if exists else insert_task(tid, tname)
    return jsonify({"ok": a > 0, "affected": a, "mode": "update" if exists else "insert"})


@bp.delete("/task")
def api_task_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    tid = (request.args.get("TaskId") or request.args.get("taskId") or "").strip()
    if not tid:
        return jsonify({"error": "TaskId required"}), 400
    if get_task_exact(tid) is None:
        return jsonify({"ok": False, "error": "代碼不存在"}), 404
    if task_in_use(tid):
        return jsonify({"ok": False, "error": "此作業已被關聯使用，無法刪除"}), 409
    a = delete_task(tid)
    return jsonify({"ok": a > 0, "affected": a})


# Program single CRUD
@bp.get("/program")
def api_program_get():
    if DB.connection_pool is None:
        return jsonify({}), 503
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    if not pid:
        return jsonify({"error": "ProgId required"}), 400
    data = get_program_exact(pid)
    if not data:
        return jsonify({}), 404
    return jsonify(data)


@bp.post("/program")
def api_program_save():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    p = request.get_json(silent=True) or {}
    pid = (p.get("ProgId") or "").strip()
    pname = (p.get("ProgName") or "").strip()
    cat = (p.get("Category") or "").strip()
    mode = (p.get("mode") or "").strip().lower()
    if not pid or not pname:
        return jsonify({"error": "ProgId and ProgName required"}), 400
    exists = get_program_exact(pid) is not None
    if mode == 'insert':
        if exists:
            return jsonify({"ok": False, "error": "代碼已存在，請更換 ProgId"}), 409
        a = insert_program(pid, pname, cat or None)
        return jsonify({"ok": a > 0, "affected": a, "mode": "insert"})
    if mode == 'update':
        if not exists:
            return jsonify({"ok": False, "error": "代碼不存在，無法更新"}), 404
        a = update_program(pid, pname, cat or None)
        return jsonify({"ok": a > 0, "affected": a, "mode": "update"})
    a = update_program(pid, pname, cat or None) if exists else insert_program(pid, pname, cat or None)
    return jsonify({"ok": a > 0, "affected": a, "mode": "update" if exists else "insert"})


@bp.delete("/program")
def api_program_delete():
    if DB.connection_pool is None:
        return jsonify({"error": "db not ready"}), 503
    pid = (request.args.get("ProgId") or request.args.get("progId") or "").strip()
    if not pid:
        return jsonify({"error": "ProgId required"}), 400
    if get_program_exact(pid) is None:
        return jsonify({"ok": False, "error": "代碼不存在"}), 404
    if program_in_use(pid):
        return jsonify({"ok": False, "error": "此程式已被關聯使用，無法刪除"}), 409
    a = delete_program(pid)
    return jsonify({"ok": a > 0, "affected": a})
