import os

os.environ["ADMIN_INITIAL_PASSWORD"] = "Admin123!"
os.environ["SEED_DEMO"] = "true"

from scripts.seed import main

main()