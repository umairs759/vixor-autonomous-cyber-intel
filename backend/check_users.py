from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.user import User

settings = get_settings()
engine = create_engine(str(settings.DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()

admin = db.query(User).filter(User.email == 'admin@example.com').first()
analyst = db.query(User).filter(User.email == 'analyst@example.com').first()

print('Admin user:')
print(f'  Email: {admin.email}')
print(f'  Role: {admin.role}')
print(f'  Is_active: {admin.is_active}')
print(f'  Failed_attempts: {admin.failed_attempts}')
print(f'  Locked_until: {admin.locked_until}')

print('Analyst user:')
analyst_email = analyst.email if analyst else "NOT FOUND"
analyst_role = analyst.role if analyst else "NOT FOUND"
analyst_is_active = analyst.is_active if analyst else "NOT FOUND"
print(f'  Email: {analyst_email}')
print(f'  Role: {analyst_role}')
print(f'  Is_active: {analyst_is_active}')

db.close()