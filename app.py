import os
from flask import Flask, render_template

def create_app() -> Flask:
    # Serve UI assets under "/assets" without changing existing HTML paths
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="ui/assets",
        static_url_path="/assets",
    )

    # Register API blueprint for dynamic data
    try:
        from api import bp as api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
    except Exception:
        # If blueprint import fails, still allow the UI to render
        pass

    @app.route("/")
    def index():
        # Render the new index page
        return render_template("DBProj01_00_Index.html")

    # Route mappings per rule.txt
    @app.route("/Unit")
    def page_unit():
        return render_template("DBProj01_01_Unit.html")

    @app.route("/Role")
    def page_role():
        return render_template("DBProj01_02_Role.html")

    @app.route("/Employee")
    def page_employee():
        # Use templates version
        return render_template("DBProj01_03_Employee.html")

    @app.route("/Task")
    def page_task():
        return render_template("DBProj01_04_Task.html")

    @app.route("/Program")
    def page_program():
        return render_template("DBProj01_05_Program.html")

    @app.route("/ListEmployee")
    def page_list_employee():
        return render_template("DBProj01_21_ListEmployeeByUnit.html")

    # Maintenance pages
    @app.route("/TaskProgs")
    def page_task_progs():
        return render_template("DBProj01_16_TaskProgs.html")

    @app.route("/RoleTasks")
    def page_role_tasks():
        return render_template("DBProj01_17_RoleTasks.html")

    @app.route("/EmployeeProg")
    def page_employee_prog():
        return render_template("DBProj01_18_EmployeeProg.html")

    # Edit page route for Unit (from rule + request)
    @app.route("/ModifyUnit")
    def page_modify_unit():
        return render_template("DBProj01_11_Unit.html")

    @app.route("/ModifyRole")
    def page_modify_role():
        return render_template("DBProj01_12_Role.html")

    @app.route("/ModifyEmployee")
    def page_modify_employee():
        return render_template("DBProj01_13_Employee.html")

    @app.route("/ModifyTask")
    def page_modify_task():
        return render_template("DBProj01_14_Task.html")

    @app.route("/ModifyProgram")
    def page_modify_program():
        return render_template("DBProj01_15_Program.html")

    return app

app = create_app()

if __name__ == "__main__":
    # 讀取環境變數（Azure 預設會設定環境變數 "WEBSITE_HOSTNAME"）
    is_azure = "WEBSITE_HOSTNAME" in os.environ

    if is_azure:
        # Azure 部署環境
        app.run(host="0.0.0.0", port=8000, debug=False)
    else:
        # 本地開發環境
        app.run(host="127.0.0.1", port=5000, debug=True)


# app = create_app()

# is_azure = bool(os.getenv("WEBSITE_HOSTNAME"))
# port = int(os.getenv("PORT") or os.getenv("WEBSITES_PORT") or 5000)
# host = "0.0.0.0" if is_azure else "127.0.0.1"
# app.run(host=host, port=port, debug=not is_azure)