
from flask_login import current_user
from app import create_app
from app.extensions import db, admin
from app.models import UserDB, UserDBView #,  ProductDB, ProductDBView, create_admin
from flask_admin import BaseView, expose
from flask import redirect, flash, url_for
from flask_bcrypt import bcrypt
from app.models import Products, ProductAdmin
import PIL
from app.models import SignupForm  #, CurrentUser, OrderDBView, OrderDB, create_domo_menu

print("Admin Email is: admin@email.com\n"
      "Admin Password is: Password01234")
print("Producer Email is: producer@email.com\n"
      "Producer Password is: Password01234")
app = create_app()


class AddStaff(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.access_level == "ADMIN"

    @expose("/", methods=["GET", "POST"])
    def index(self):
        form = SignupForm()

        if form.validate_on_submit():
            new_user = CurrentUser(form.email.data,
                                   bcrypt.hashpw(form.password.data.encode("utf-8"), bcrypt.gensalt()),
                                   form.name.data,
                                   "S")

            if new_user.check_for_dup_emails():
                flash("Email address is already used!", "info")
                return redirect(url_for(".index"))
            else:
                new_user.add_user_to_db()
                flash(f"{new_user.name} was successfully add as a Staff Member!", "success")
                return redirect(url_for(".index"))
        return self.render("admin/addStaff.html", form=form)


class LogOut(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.access_level == "ADMIN"

    @expose("/")
    def index(self):
        return redirect("/logout")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        admin.add_view(UserDBView(UserDB, db.session, name="User Accounts"))
        admin.add_view(ProductAdmin(Products, db.session, name="Add Product Items"))
        admin.add_view(LogOut(name="Log Out"))
        app.run()
