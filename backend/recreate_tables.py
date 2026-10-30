import os
import sys

# Ensure we can import from the parent project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import and create tables
from app.database import Base, engine

import app.models  # noqa: F401 - populate Base.metadata with all models

Base.metadata.create_all(bind=engine)
print("Tables created successfully")
