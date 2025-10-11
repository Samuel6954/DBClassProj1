ERP 稽核輔助系統（Flask + PostgreSQL）

專案簡介

- 一個以 Flask 打造的教學專案，透過 REST API 搭配前端模板完成「單位、權限、員工、作業、程式」等基礎資料維護，並支援查詢、及多對多關聯維護（RoleTasks、TaskProgs、EmployeeProgs）。
- 前端以原生 fetch 呼叫後端 API，樣式使用 `ui/assets/tech.css`，模板放在 `templates/`。
- 資料庫為 PostgreSQL，連線以 `psycopg2.pool.SimpleConnectionPool` 管理，環境變數由 `.env` 提供。

重點功能

- 基礎資料維護頁面
  - 單位代碼管理：/Unit、維護：/ModifyUnit
  - 系統權限管理：/Role、維護：/ModifyRole
  - 員工資料管理：/Employee、維護：/ModifyEmployee
  - 作業目錄管理：/Task、維護：/ModifyTask
  - 程式代碼管理：/Program、維護：/ModifyProgram
- 關聯維護頁面（多對多）
  - 作業可用程式維護：/TaskProgs?TaskId=…（Task ↔ Program）
  - 權限可用作業維護：/RoleTasks?RoleId=…（Role ↔ Task）
  - 員工常用程式維護：/EmployeeProg?EmployeeId=…（Employee ↔ Program）
- 稽核查詢頁
  - 依單位展開員工，並可按員工顯示其權限作業對應程式：/ListEmployee

專案結構

- app.py：Flask 入口，註冊 Blueprint 與頁面路由；靜態資源 `/assets` 指向 `ui/assets`。
- api/
  - **init**.py：建立 Blueprint `bp` 並掛載在 `/api`。
  - api.py：所有 REST API 路由（查詢/CRUD/關聯維護/健康檢查）。
  - sql.py：連線池與 SQL 封裝（fetchall/fetchone/execute），各資料表的存取函式與關聯維護函式。
- templates/：所有頁面模板（對應上方路由）。
- ui/assets/：共用樣式 `tech.css`。
- ERP.sql：資料表 schema 與範例（可自行載入到 PostgreSQL）。
- requirements.txt：Python 套件需求。

安裝與執行

1. 建立並啟用虛擬環境（可用 venv 或 conda）

- Python 3.10 建議

2. 安裝套件

- pip install -r requirements.txt

3. 設定資料庫連線

- 複製 `.env.example` 為 `.env`，填入以下必填參數：
  - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

4. 建置資料庫（選用）

- 若是全新資料庫，可將 `ERP.sql` 匯入 PostgreSQL 建立表與初始資料。

5. 啟動服務

- python app.py
- 瀏覽器開啟 http://127.0.0.1:5000/

主要頁面與路由

- 首頁：/ → templates/DBProj01_00_Index.html
- 基礎資料
  - /Unit, /Role, /Employee, /Task, /Program
  - 維護頁：/ModifyUnit, /ModifyRole, /ModifyEmployee, /ModifyTask, /ModifyProgram
- 關聯維護
  - /TaskProgs?TaskId=…（作業 ↔ 程式）
  - /RoleTasks?RoleId=…（權限 ↔ 作業）
  - /EmployeeProg?EmployeeId=…（員工 ↔ 程式）
- 稽核查詢
  - /ListEmployee（依單位 → 員工 → 權限 → 程式）

API 速覽（/api）

- 健康檢查
  - GET /api/db/health → { connected, error }
  - GET /api/db/info → 目前資料庫/使用者/search_path
- 單位（Unit）
  - GET /api/units?UnitId=&UnitName=&ManagerUser=
  - GET /api/units/all?limit=&offset=
  - GET /api/unit?UnitId=…
  - POST /api/unit { UnitId, UnitName, ManagerUser?, WorkIntroduce?, mode: 'insert'|'update' }
  - DELETE /api/unit?UnitId=…
- 權限（Role）
  - GET /api/roles?RoleId=&RoleName=&VisibleMark=
  - GET /api/role?RoleId=…
  - POST /api/role { RoleId, RoleName, VisibleMark, mode }
  - DELETE /api/role?RoleId=…
  - 關聯：
    - GET /api/role/tasks?RoleId=…
    - POST /api/role/tasks { RoleId, TaskIds: [] }
    - DELETE /api/role/tasks?RoleId=…&TaskId=…
    - GET /api/role/programs?RoleId=…（透過 RoleTasks→TaskProgs→Program 聚合）
- 員工（Employee）
  - GET /api/employees?EmployeeId=&EmployeeName=&UnitId=&RoleId=
  - GET /api/employee?EmployeeId=…
  - GET /api/employees/exists?EmployeeId=…
  - POST /api/employee { EmployeeId, EmployeeName, UnitId, JobName?, RoleId, mode }
  - DELETE /api/employee?EmployeeId=…
  - 關聯：
    - GET /api/employee/programs?EmployeeId=…
    - POST /api/employee/programs { EmployeeId, ProgIds: [] }
    - DELETE /api/employee/programs?EmployeeId=…&ProgId=…
- 作業（Task）
  - GET /api/tasks → 簡易清單（[{ id, name }])
  - GET /api/tasks2?TaskId=&TaskName= → 查詢 Task
  - GET /api/task?TaskId=…／POST /api/task／DELETE /api/task
- 程式（Program）
  - GET /api/programs?ProgId=&ProgName=&Category=（Category 欄位非必備）
  - GET /api/program?ProgId=…／POST /api/program／DELETE /api/program
  - 關聯：
    - GET /api/task/programs?TaskId=…
    - POST /api/task/programs { TaskId, ProgIds: [] }
    - DELETE /api/task/programs?TaskId=…&ProgId=…

資料庫 Schema 概要（見 ERP.sql）

- Role(RoleId, RoleName, VisibleMark)
- Unit(UnitId, UnitName, WorkIntroduce, ManagerUser → FK Employee.EmployeeId)
- Employee(EmployeeId, EmployeeName, UnitId → FK, JobName, RoleId → FK)
- Task(TaskId, TaskName)
- Program(ProgId, ProgName[, Category?])
- RoleTasks(RoleId, TaskId) 主鍵複合 (RoleId, TaskId)
- TaskProgs(TaskId, ProgId) 主鍵複合 (TaskId, ProgId)
- EmployeeProgs(EmployeeId, ProgId) 主鍵複合 (EmployeeId, ProgId)

開發說明

- `.env` 於 import 時自動載入（api/sql.py 的 `load_dotenv()`）。連線池在模組載入時初始化。
- 若環境變數未設定或無法連線，API 會回傳空陣列或 503（依端點實作）。
- `Program.Category` 欄位為相容性選擇：後端會自動偵測，如資料庫無此欄位則以空字串回傳並避開過濾條件。

常見操作（cURL 範例）

- 新增權限的作業清單：
  curl -X POST http://127.0.0.1:5000/api/role/tasks \
   -H "Content-Type: application/json" \
   -d '{"RoleId":"HR-ADMIN","TaskIds":["TASK-RECRUIT","TASK-ONBOARD"]}'

- 將多個程式加入某作業：
  curl -X POST http://127.0.0.1:5000/api/task/programs \
   -H "Content-Type: application/json" \
   -d '{"TaskId":"TASK-RECRUIT","ProgIds":["PRG001","PRG002"]}'

- 新增員工常用程式：
  curl -X POST http://127.0.0.1:5000/api/employee/programs \
   -H "Content-Type: application/json" \
   -d '{"EmployeeId":"E0001","ProgIds":["PRG001","PRG002"]}'

開發/調試小提醒

- 首頁與各管理頁不會預設載入大量資料；按查詢或選擇條件後再呼叫 API。
- 若要確認資料庫連線是否正常，可先呼叫 `/api/db/health` 與 `/api/db/info`。
- 靜態樣式載於 `/assets/tech.css`，由 `app.py` 將 `ui/assets` 映射到 `/assets`。

授權

- 僅供課程與教學用途。請依實際需求調整與擴充。
