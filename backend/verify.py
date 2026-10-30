from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.security import verify_password
from app.models.user import User

settings = get_settings()
engine = create_engine(str(settings.DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()

# Check admin
admin = db.query(User).filter(User.email == 'admin@example.com').first()
print('=== Admin User ===')
print(f'Email: {admin.email}')
print(f'Role: {admin.role}')
print(f'Is_active: {admin.is_active}')
print(f'Failed_attempts: {admin.failed_attempts}')
print(f'Locked_until: {admin.locked_until}')
print(f'Password hash starts with: {admin.password_hash[:20]}...')

# Check analyst
analyst = db.query(User).filter(User.email == 'analyst@example.com').first()
print()
print('=== Analyst User ===')
print(f'Email: {analyst.email}')
print(f'Role: {analyst.role}')
print(f'Is_active: {analyst.is_active}')

# Verify Argon2 hash matches Admin123!
print()
print('=== Password Verification ===')
result = verify_password('Admin123!', admin.password_hash)
print(f'verify_password(Admin123!, admin.hash[:20]...): {result}')

db.close()