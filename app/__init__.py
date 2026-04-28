
from app.extensions import db, login_manager, admin, bootstrap
from app.models import UserDB
from flask_admin import expose, AdminIndexView
from flask import Flask, redirect, flash
from flask_login import current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

# Create Bcrypt instance
bcrypt = Bcrypt()



class AdminHome(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.access_level == "ADMIN"

    def inaccessible_callback(self, name, **kwargs):
        flash("You must be signed in as Admin!", "warning")
        return redirect("/")

    @expose("/")
    def index(self):
        flash(f"Welcome {current_user.fname}!", "success")
        return self.render("admin/index.html")


def create_app(config_class="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_class)

    @login_manager.user_loader
    def load_user(user_id):
        return UserDB.query.get(int(user_id))



    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    admin.init_app(app, index_view=AdminHome())
    bootstrap.init_app(app)
    bcrypt.init_app(app)   # <-- IMPORTANT

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)




    return app
