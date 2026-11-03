
import sqlite3

db_path = r"C:\Users\LENOVO\Downloads\veltrix_assessment\veltrix_assessment\veltrix.db"

conn = sqlite3.connect(db_path)

query = """
SELECT
    m.employee_id,
    COUNT(e.employee_id) AS team_size
FROM employees AS m
LEFT JOIN employees AS e
    ON e.manager_id = m.employee_id
WHERE m.role = 'manager'
GROUP BY m.employee_id
ORDER BY m.employee_id
"""

for row in conn.execute(query):
    print(row)

conn.close()
