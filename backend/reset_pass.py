from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.security import hash_password
from app.models.user import User

settings = get_settings()
engine = create_engine(str(settings.DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()
try:
    user = db.query(User).filter(User.email == "admin@example.com").first()
    if not user:
        user = User(email="admin@example.com", role="admin", is_active=True)
        db.add(user)
    user.password_hash = hash_password("Admin123!")
    user.failed_attempts = 0
    user.locked_until = None
    user.is_active = True
    db.commit()
    print(">>> PASSWORD_UPDATE_SUCCESSFUL: Admin123! <<<")
finally:
    db.close()
