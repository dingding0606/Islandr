'''
@Description: Factory Function
@Author: Tianyi Lu
@Date: 2019-08-10 11:09:09
@LastEditors: Tianyi Lu
@LastEditTime: 2019-08-13 13:35:51
'''
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_avatars import Avatars
from .flask_msearch import Search
from config import config
from flask_apscheduler import APScheduler
from flask_jsglue import JSGlue



bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
login_manager = LoginManager()
avatars = Avatars()
search = Search(db=db)
login_manager.login_view = 'auth.login'
scheduler =APScheduler()
jsglue = JSGlue()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    jsglue.init_app(app)

    if not config_name == 'testing':
        scheduler.init_app(app)
        scheduler.start()

    avatars.init_app(app)
    search.init_app(app)

    if app.config['SSL_REDIRECT']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    from .job import send_bulletin, add_reminder
    from flask import current_app
    with app.app_context():
        send_bulletin(current_app._get_current_object())
        add_reminder(current_app._get_current_object())


    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .event import event as event_blueprint
    app.register_blueprint(event_blueprint, url_prefix='/event')

    from .group import group as group_blueprint
    app.register_blueprint(group_blueprint, url_prefix='/group')

    from .moment import moment as moment_blueprint
    app.register_blueprint(moment_blueprint, url_prefix='/moment')

    from .egg import egg as egg_blueprint
    app.register_blueprint(egg_blueprint)

    return app
