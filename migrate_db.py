from models import Base, engine

# Drop all tables and recreate
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

print("Database migrated successfully!")
