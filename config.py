
import os
from dotenv import load_dotenv



class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv()
    SECRET_KEY = os.getenv("SECRET_KEY")
    db_name = os.getenv("DB_NAME", "default.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, db_name)}"
    print(SQLALCHEMY_DATABASE_URI)
    FLASK_ADMIN_SWATCH = "slate"
    UPLOAD_FOLDER = "app/static"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
