import os
from datetime import timedelta

class Config:
    uri = os.getenv('DATABASE_URI', 'mysql+pymysql://root:hardik%401310@localhost:3306/QVDB')
    # Aiven/Render use 'mysql://' which defaults to mysql-python (not installed)
    if uri.startswith("mysql://"):
        uri = uri.replace("mysql://", "mysql+pymysql://", 1)
        
    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
