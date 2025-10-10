-- 1) 系統權限 (Role)
CREATE TABLE "Role" (
"RoleId" varchar(10) PRIMARY KEY,
"RoleName" varchar(10) NOT NULL,
"VisibleMark" boolean NOT NULL DEFAULT true
);
-- 2) 單位 (Unit)
CREATE TABLE "Unit" (
"UnitId" varchar(10) PRIMARY KEY,
"UnitName" varchar(10) NOT NULL,
"WorkIntroduce" text,
"ManagerUser" varchar(10) NULL -- 之後加 FK 指向 Employee(EmployeeId)
);
-- 3) 員工 (Employee)
CREATE TABLE "Employee" (
"EmployeeId" varchar(10) PRIMARY KEY,
"EmployeeName" varchar(20) NOT NULL,
"UnitId" varchar(10) NOT NULL,
"JobName" varchar(10),
"RoleId" varchar(6) NOT NULL,
CONSTRAINT fk_employee_unit
FOREIGN KEY ("UnitId")
REFERENCES "Unit"("UnitId")
ON UPDATE CASCADE ON DELETE RESTRICT,
CONSTRAINT fk_employee_role
FOREIGN KEY ("RoleId")
REFERENCES "Role"("RoleId")
ON UPDATE CASCADE ON DELETE RESTRICT
);
-- 4) 作業目錄 (Task)
CREATE TABLE "Task" (
"TaskId" varchar(10) PRIMARY KEY,
"TaskName" varchar(20) NOT NULL
);
-- 5) 程式 (Program)
CREATE TABLE "Program" (
"ProgId" varchar(20) PRIMARY KEY,
"ProgName" varchar(20) NOT NULL
);
-- 6) 系統權限 × 作業目錄 (RoleTasks) 多對多交集表
CREATE TABLE "RoleTasks" (
"RoleId" varchar(10) NOT NULL,
"TaskId" varchar(10) NOT NULL,
PRIMARY KEY ("RoleId","TaskId"),
CONSTRAINT fk_roletasks_role
FOREIGN KEY ("RoleId")
REFERENCES "Role"("RoleId")
ON UPDATE CASCADE ON DELETE CASCADE,
CONSTRAINT fk_roletasks_task
FOREIGN KEY ("TaskId")
REFERENCES "Task"("TaskId")
ON UPDATE CASCADE ON DELETE CASCADE
);
-- 7) 作業目錄 × 程式 (TaskProgs) 多對多交集表
CREATE TABLE "TaskProgs" (
"TaskId" varchar(10) NOT NULL,
"ProgId" varchar(10) NOT NULL,
PRIMARY KEY ("TaskId","ProgId"),
CONSTRAINT fk_taskprogs_task
FOREIGN KEY ("TaskId")
REFERENCES "Task"("TaskId")
ON UPDATE CASCADE ON DELETE CASCADE,
CONSTRAINT fk_taskprogs_prog
FOREIGN KEY ("ProgId")
REFERENCES "Program"("ProgId")
ON UPDATE CASCADE ON DELETE CASCADE
);
-- 8) 員工常用程式清單 (EmployeeProgs) 多對多交集表
CREATE TABLE "EmployeeProgs" (
"EmployeeId" varchar(10) NOT NULL,
"ProgId" varchar(10) NOT NULL,
PRIMARY KEY ("EmployeeId","ProgId"),
CONSTRAINT fk_emp_progs_emp
FOREIGN KEY ("EmployeeId")
REFERENCES "Employee"("EmployeeId")
ON UPDATE CASCADE ON DELETE CASCADE,
CONSTRAINT fk_emp_progs_prog
FOREIGN KEY ("ProgId")
REFERENCES "Program"("ProgId")
ON UPDATE CASCADE ON DELETE CASCADE
);
-- 9) 補上單位的主管外鍵（避免循環相依，放在最後）
ALTER TABLE "Unit"
ADD CONSTRAINT fk_unit_manager
FOREIGN KEY ("ManagerUser")
REFERENCES "Employee"("EmployeeId")
ON UPDATE CASCADE
ON DELETE SET NULL;

-- Seed demo Units for development
INSERT INTO "Unit" ("UnitId","UnitName","WorkIntroduce","ManagerUser") VALUES
  ('HR01','人力資源處','人員招募、報到、離職','U0001')
ON CONFLICT ("UnitId") DO NOTHING;
INSERT INTO "Unit" ("UnitId","UnitName","WorkIntroduce","ManagerUser") VALUES
  ('HR001','人力資源部','人員招募、報到、離職','U0001')
ON CONFLICT ("UnitId") DO NOTHING;
INSERT INTO "Unit" ("UnitId","UnitName","WorkIntroduce","ManagerUser") VALUES
  ('IT01','資訊處','系統維運與開發','U0002')
ON CONFLICT ("UnitId") DO NOTHING;
