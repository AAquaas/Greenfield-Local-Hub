
from flask_wtf import FlaskForm
from sqlalchemy.sql.functions import current_user
from sqlalchemy.orm import relationship
from wtforms.fields import EmailField, PasswordField, StringField, DecimalField, FileField, SelectField, BooleanField, DateTimeLocalField, FloatField, SubmitField
from wtforms.validators import InputRequired, DataRequired, NumberRange, Length, EqualTo
from flask_wtf.file import FileRequired, FileAllowed
from flask_bcrypt import generate_password_hash
from flask_login import UserMixin, current_user
from flask_admin.contrib.sqla import ModelView
from flask_admin.form.upload import ImageUploadField
from flask_admin import Admin
import os
import uuid


from app.extensions import db, login_manager


admin = Admin()



class UserDB(db.Model, UserMixin):
    __tablename__ = "account"
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(9), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    loyalty_points = db.Column(db.Integer, nullable=False, default=0)
    producer_bio = db.Column(db.String(500), nullable=False, default="NO PRODUCER BIO SET")
    access_level = db.Column(db.String(20), nullable=False, default="USER")

    orders = relationship("Orders", back_populates="user")


    @property
    def __repr__(self):
        return f"<UserDB: {self.userID}, {self.email}, {self.password}, {self.access_level}, {self.fname}, {self.lname}, {self.postcode}, {self.address}>"

class Products(db.Model):
    __tablename__ = "product"
    product_id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer)
    product_name = db.Column(db.Unicode(64))
    product_price = db.Column(db.Numeric(10,2), nullable=False)
    product_type = db.Column(db.String(30), nullable=False)
    product_stock = db.Column(db.Integer, nullable=False)
    file_image = db.Column(db.String(30), nullable=False)

    CartItem = relationship("CartItem", back_populates="Products")

    @property
    def __unicode__(self):
        return f'<product {self.product_name}>'


class Orders(db.Model):
    __tablename__ = "orders"
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    order_type = db.Column(db.String(64))
    postcode = db.Column(db.String(9), nullable=True)
    address = db.Column(db.String(100), nullable=True)
    order_date = db.Column(db.String(30), nullable=False)
    order_total = db.Column(db.Numeric(10,2), nullable=False)
    order_status = db.Column(db.String(30), nullable=False, default="IN PROGRESS")

    user = relationship("UserDB", back_populates="orders")

    @property
    def __unicode__(self):
        return f'<product {self.order_id}>'



def rename_file(obj, file_data):
    ext = os.path.splitext(file_data.filename)[1]
    return f"{uuid.uuid4().hex}{ext}"

class ProductAdmin(ModelView):
    column_list = ('product_name', 'product_price', 'product_type', 'product_stock', 'file_image')
    form_columns = ('product_name', 'product_price', 'product_type', 'product_stock', 'file_image')
    column_searchable_list = ('product_name', 'product_type')
    column_filters = ('product_type', 'product_price')

    form_extra_fields = {
        'file_image': ImageUploadField(
            'Image',
            base_path=os.path.join(os.path.dirname(__file__), 'static/Images'),  # static folder
            url_relative_path='',  # empty because base_path is already static
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=rename_file,
            allow_overwrite=False
        )
    }

class UserDBView(ModelView):
    column_list = ('fname', 'lname', 'email', 'password', 'postcode', 'address', 'access_level')
    form_columns = ('fname', 'lname', 'email', 'password', 'postcode', 'address', 'access_level')
    column_searchable_list = ('email',)
    column_filters = ('fname', 'lname')

    def on_model_change(self, form, model, is_created):
        if form.password.data:
            # Hash plain text and decode bytes to string for DB storage
            model.password = generate_password_hash(form.password.data).decode('utf-8')


class CartItem(db.Model):
    __tablename__ = "cartitem"
    cart_id = db.Column(db.Integer, primary_key=True) # Unique ID for every row
    cart_name = db.Column(db.String(20), nullable=False) # Groups items (e.g., 'cart_1')
    quantity = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(10), default='active', nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=True)
    Products = relationship("Products", back_populates="CartItem")

    def __repr__(self):
        return f'<cartitem {self.cart_name} (x{self.quantity}) - {self.status}>'





class SignupForm(FlaskForm):
    email = EmailField("Email:", validators=[InputRequired()])
    password = PasswordField("Password:", validators=[InputRequired()])
    fname = StringField("First Name:", validators=[InputRequired()])
    lname = StringField("First Name:", validators=[InputRequired()])
    postcode = StringField("Postcode:", validators=[InputRequired()])
    address = StringField("Address:", validators=[InputRequired()])

class LoginForm(FlaskForm):
    name = StringField("Email:", validators=[InputRequired()])
    password = PasswordField("Password:", validators=[InputRequired()])

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password',validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, message="Password must be at least 6characters.")])
    confirm_password = PasswordField('Confirm New Password',validators=[DataRequired(), EqualTo('new_password', message="Passwords must match.")])
    submit = SubmitField('Change Password')
