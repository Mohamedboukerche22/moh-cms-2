import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import humanize


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure logging
logging.basicConfig(level=logging.DEBUG)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///cms.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# configure uploads
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create admin



    from models import User

    from werkzeug.security import generate_password_hash

    

    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@cms.local',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            full_name='Administrator'
        )
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Created default admin user: admin/admin123")

import routes

#dont use this 
#@app.template_filter('datetime')
#def format_datetime(value, format='%Y-%m-%d %H:%M'):
 #   if isinstance(value, datetime):
  #      return value.strftime(format)
   # return value


@app.template_filter('naturaltime')
def naturaltime_filter(dt):
    return humanize.naturaltime(datetime.now() - dt)
