from storage.database import engine


try:
    with engine.connect() as connection:
        print("DATABASE CONNECTION: SUCCESS")
        print("SQLite database is ready.")

except Exception as error:
    print("DATABASE CONNECTION: FAILED")
    print(error)