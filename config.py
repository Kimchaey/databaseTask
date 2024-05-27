class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://cwkim:2023103921@ibiz.khu.ac.kr/cwkim'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your_secret_key'
    WTF_CSRF_ENABLED = False
