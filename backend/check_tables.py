from sqlalchemy import inspect

from storage.database import engine


inspector = inspect(engine)

tables = inspector.get_table_names()

print("DATABASE TABLES")
print("================")

for table in tables:
    print("-", table)