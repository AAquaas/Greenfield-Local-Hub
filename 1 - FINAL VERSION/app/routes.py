import flask_login
from flask import Blueprint, render_template, flash, redirect, session, request, url_for, current_app
from flask import session as login_session
from flask_login import login_required, login_user, logout_user, current_user
from flask_bcrypt import Bcrypt, check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app.models import SignupForm, LoginForm, UserDB, ChangePasswordForm, Products, Orders
from app.extensions import db
from app.models import Products, CartItem
import requests
import os
import datetime
from werkzeug.utils import secure_filename

import stripe
client = stripe.StripeClient('sk_test_51T4LU0Q4E58lH7LGvmMrPp3pmiT764Vn6z3DSGMSMBCNW3BC35s8S9PdMGqxbfTegYYN3xM7nZa06xOOHHBRQebQ00um76wAOP')

main = Blueprint("main", __name__)
bcrypt = Bcrypt()


@main.route("/")
def home():
    return render_template("home.html")


@main.route("/terms")
def terms():
    return render_template("terms.html")


@main.route("/privacy")
def privacy():
    return render_template("privacy.html")


@main.route("/cookies")
def cookies():
    return render_template("cookies.html")


@main.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = current_user  # Flask-Login ensures the user is logged in
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Check current password
        if not check_password_hash(user.password, form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for('main.change_password'))

        # Update password
        user.password = generate_password_hash(form.new_password.data).decode('utf-8')
        db.session.commit()
        flash("Password successfully changed!", "success")
        return redirect(url_for('main.home'))

    return render_template('change_password.html', form=form)


@main.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form['email']
        password = request.form['password']
        postcode = request.form['postcode']
        address = request.form['address']
        terms = request.form['terms']
        hashed_password = bcrypt.generate_password_hash(
            password).decode('utf-8')

        checkemail = UserDB.query.filter(UserDB.email == email).first()
        checkuser = UserDB.query.filter(UserDB.fname == fname).first()

        if not terms:
            flash("Please accept our terms to continue")

        if checkemail != None:
            flash("Please register using a different email.")

            return render_template("signup.html", subtitle="Register")
        elif checkuser is not None:
            flash("Username already exists !")

            return render_template("signup.html")

        else:
            new_customer = UserDB(fname=fname, lname=lname, email=email, password=hashed_password, postcode=postcode,
                                  address=address)
            db.session.add(new_customer)
            db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('signup.html')


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        customer = UserDB.query.filter_by(email=email).first()
        if customer and bcrypt.check_password_hash(customer.password, password):
            #    db.session["user_id"] = customer.id
            login_user(customer)
            return redirect(url_for('main.home'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('main.login'))
    return render_template('login.html', subtitle="Login")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect("/login")


@main.route("/products")
@login_required
def products():
    all_products = Products.query.all()
    return render_template('products.html', product=all_products)


@main.route("/productView", methods=['GET', 'POST'])
@login_required
def productView():
    selected_menu = request.args.get('type')
    products = Products.query.filter(Products.product_name == selected_menu).first()
    price = products.product_price
    stock = products.product_stock
    pid = products.product_id
    name = products.product_name
    image = products.file_image
    print(f"Loading view for: {products.product_name}")

    quantity = db.session.query(CartItem.quantity).filter_by(product_id=pid).scalar()

    return render_template('product_view.html', product_name=name, product_price=price, product_id=pid,
                           product_stock=stock, file_image=image, quantity=quantity)


@main.route('/addtocart', methods=['POST'])
@login_required
def addtocart():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("name_of_slider"))

    try:
        # 1. Find the highest cart number the user has ever had
        prefix = f"user_{current_user.id}_cart_"
        all_user_items = CartItem.query.filter(CartItem.cart_name.like(f"{prefix}%")).all()

        if all_user_items:
            # Get the highest number (e.g., if they have cart_1 and cart_2, this is 2)
            current_no = max([int(item.cart_name.split('_')[-1]) for item in all_user_items])
        else:
            current_no = 1

        # 2. Check if that specific cart number is still 'active'
        # If it is 'closed' or 'paid', we increment the number to open a NEW cart
        active_cart = CartItem.query.filter_by(
            cart_name=f"{prefix}{current_no}",
            status='active'
        ).first()

        if not active_cart and all_user_items:
            # The latest cart was finished/paid, so we start a new number
            current_no += 1

        active_label = f"{prefix}{current_no}"

        # 3. Add item to the active cart
        # Check if this specific product is already in the CURRENT active cart
        existing_item = CartItem.query.filter_by(
            cart_name=active_label,
            product_id=product_id,
            status='active'
        ).first()

        if existing_item:
            existing_item.quantity = quantity
        else:
            new_item = CartItem(
                cart_name=active_label,
                quantity=quantity,
                product_id=product_id,
                status='active'  # Set it as active
            )
            db.session.add(new_item)

        db.session.commit()
        flash(f"Added to {active_label.replace('_', ' ').title()}")
        return redirect(url_for('main.products'))

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        return redirect(url_for('main.products'))

@main.route('/cart', methods=["GET", "POST"])
@login_required
def cart():
    cartitems = db.session.query(
        CartItem.quantity,
        Products.product_name,
        Products.product_price,
        CartItem.product_id
    ).join(Products, CartItem.product_id == Products.product_id).all()

    raw_points = session.get('points_using')
    points_used = float((raw_points) if raw_points else 0)
    pennies = points_used * 0.01

    subtotal = sum(item.quantity * item.product_price for item in cartitems)

    # Subtract points and ensure total isn't negative
    grand_total = max(0, float(subtotal) - float(pennies or 0))
    session['grand_total'] = grand_total




    return render_template('cart.html', cartitems=cartitems, grand_total=grand_total, points_used=points_used)


@main.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():

    session['order_type'] = request.form.get('order_type')
    session['postcode'] = request.form.get('postcode')
    session['address'] = request.form.get('address')

    # 1. Get raw total (might be "£10.50" or "1,200.00")
    raw_total = str(session.get('grand_total', '0'))

    # 2. Clean the string: remove £ and commas
    clean_total = raw_total.replace('£', '').replace(',', '').strip()
    session['clean_total'] = clean_total
    try:
        # 3. Convert to float first, then to pence for Stripe
        total_in_pence = int(float(clean_total) * 100)

        checkout_session = client.v1.checkout.sessions.create(params={
            'line_items': [{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {'name': 'Total Amount'},
                    'unit_amount': total_in_pence,
                },
                'quantity': 1,
            }],
            'mode': 'payment',
            'success_url': f'http://127.0.0.1:5000/success?amount={clean_total}',
            'cancel_url': f'http://127.0.0.1:5000/cancel?amount={clean_total}',
        })
    except Exception as e:
        return f"Checkout Error: {str(e)}"

    return redirect(checkout_session.url, code=303)


@main.route('/success')
@login_required
def success():
    # 1. Prevent double-processing if page is refreshed
    if 'clean_total' not in session:
        return redirect(url_for('main.home'))

    # 2. Safely retrieve the total and ensure it is a number
    try:
        total = float(session.get('clean_total'))
        total_display = session.get('clean_total')
    except (TypeError, ValueError):
        return redirect(url_for('main.home'))

    # 3. Gather session data
    clean_total = str(total)
    order_type = str(session.get('order_type', 'Collection'))
    postcode = str(session.get('postcode', 'N/A'))
    address = str(session.get('address', 'N/A'))

    if order_type == "Collection":
        postcode = "N/A"
        address = "N/A"

    # 4. Create the Order record
    order_date = datetime.datetime.now().strftime("%d-%m-%Y")
    new_order = Orders(
        user_id=current_user.id,
        order_type=order_type,
        postcode=postcode,
        address=address,
        order_date=order_date,
        order_total=clean_total
    )
    db.session.add(new_order)

    # 5. Clear the user's active cart items
    # Adjusting this based on your prefix logic in 'addtocart'
    prefix = f"user_{current_user.id}_cart_"
    items = CartItem.query.filter(CartItem.cart_name.like(f"{prefix}%")).all()

    for item in items:
        product = Products.query.get(item.cart_id)
        if product:
            # Subtract the quantity the user took
            product.product_stock -= item.quantity
        else:
            print(f"Warning: Product with ID {item.cart_id} not found.")

    CartItem.query.filter(CartItem.cart_name.like(f"{prefix}%")).delete(synchronize_session=False)

    # 6. Award Loyalty Points (Fixes the TypeError)
    extra_points = int(total * 10)
    current_user.loyalty_points = (current_user.loyalty_points or 0) + extra_points

    points_to_subtract = int(session.get('points_using') or 0)

    # 2. Subtract from the user's total
    current_user.loyalty_points -= points_to_subtract

    session['points_using'] = 0

    # 7. Save changes to DB and clear the session flag
    db.session.commit()
    session.pop('clean_total', None)

    return render_template('success.html', clean_total=total_display)


@main.route('/cancel')
def cancel():
    clean_total = str(session.get('clean_total', 0))
    print(clean_total)
    return render_template ('cancel.html', clean_total=clean_total)

@main.route('/order_history', methods=["GET"])
@login_required
def order_history():

    orderitems = db.session.query(
        Orders.order_type,
        Orders.order_date,
        Orders.order_total,
        Orders.order_status
    ).filter(Orders.user_id == current_user.id).all()

    return render_template('order_history.html', orderitems=orderitems)

@main.route('/our_producers', methods=["GET"])
def producer():
    producers = db.session.query(
        UserDB.fname,
        UserDB.lname,
        UserDB.producer_bio
    ).filter(UserDB.access_level == "PRODUCER").all()

    return render_template('our_producers.html', producers=producers)

@main.route('/addproducts', methods=['GET', 'POST'])
def addproducts():
    if current_user.access_level != "PRODUCER":
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        product_name = request.form['product_name']
        product_price = float(request.form['product_price'])
        product_type = request.form['product_type']
        product_stock = int(request.form['product_stock'])
        producer_id = current_user.id

        # 2. File Check
        if 'file1' not in request.files:
            return 'There is no file1 in form!'

        file1 = request.files['file1']

        if file1.filename == '':
            return 'No selected file'

        if file1:
            # 3. Secure and Save
            filename = secure_filename(file1.filename)
            # This points to your static/images folder
            upload_path = os.path.join(current_app.root_path, 'static', 'images', filename)
            file1.save(upload_path)

            # 4. Save to Database
            # We save 'images/filename' so url_for('static', filename=file_image) works later
            image_db_path = f'{filename}'

            new_product = Products(
                product_name=product_name,
                product_price=product_price,
                product_type=product_type,
                file_image=image_db_path,
                producer_id=producer_id,
                product_stock=product_stock
            )
            db.session.add(new_product)
            db.session.commit()

            return redirect(url_for('main.products'))

    return render_template('add_items.html')

@main.route('/producer-info', methods=['GET', 'POST'])
def producer_info():
    if current_user.access_level != "PRODUCER":
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        bio = request.form['bio']
        current_user.producer_bio = bio
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('producer_info.html')

@main.route('/update-product', methods=['GET'])
def update_product():
    if current_user.access_level != "PRODUCER":
        return redirect(url_for('main.home'))
    else:
        products = Products.query.filter_by(producer_id=current_user.id).all()
        return render_template('update_product.html', products=products)


@main.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if current_user.access_level != "PRODUCER":
        return redirect(url_for('main.home'))

    product = Products.query.get_or_404(product_id)

    if request.method == 'POST':
        # 1. Update Text Fields
        product.product_name = request.form.get('product_name')
        product.product_price = request.form.get('product_price')
        product.product_type = request.form.get('product_type')
        product.product_stock = request.form.get('product_stock')

        # 2. Handle File Upload (Optional)
        file1 = request.files.get('file1')
        if file1 and file1.filename != '':
            filename = secure_filename(file1.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'images', filename)
            file1.save(upload_path)
            product.file_image = filename  # Only update image if a new one is uploaded

        db.session.commit()
        return redirect(url_for('main.home'))  # Redirect to home or list after success

    # This only runs on GET requests
    return render_template('edit_product.html', product=product)


@main.route('/delete_product/<int:product_id>', methods=['GET', 'POST'])
def delete_product(product_id):
    product = Products.query.get_or_404(product_id)
    print(f"DEBUG: Found product {product.product_name}")

    try:
        # 2. Delete CartItems using a direct query (bypasses relationship issues)
        num_cart_deleted = CartItem.query.filter_by(product_id=product_id).delete()
        print(f"DEBUG: Deleted {num_cart_deleted} items from cart")

        # 3. Delete the product itself
        db.session.delete(product)

        # 4. Commit and check for errors
        db.session.commit()
        print("DEBUG: Database commit successful")

    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: DELETE FAILED! Error: {e}")
        # If this prints, it will tell you exactly why (e.g., Foreign Key Constraint)

    return redirect(url_for('main.update_product'))

@main.route('/delete_cartitem/<int:product_id>', methods=['GET', 'POST'])
def delete_cartitem(product_id):
    cart_item = CartItem.query.get_or_404(product_id)
    print(f"DEBUG: Found product {CartItem.product_id}")

    try:
        # 2. Delete CartItems using a direct query (bypasses relationship issues)
        num_cart_deleted = CartItem.query.filter_by(product_id=product_id).delete()
        print(f"DEBUG: Deleted {num_cart_deleted} items from cart")

        # 3. Delete the product itself
        db.session.delete(cart_item)

        # 4. Commit and check for errors
        db.session.commit()
        print("DEBUG: Database commit successful")

    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: DELETE FAILED! Error: {e}")
        # If this prints, it will tell you exactly why (e.g., Foreign Key Constraint)

    return redirect(url_for('main.cart'))

@main.route('/user_update', methods=['GET', 'POST'])
@login_required
def user_update():
    if request.method == "POST":
        current_user.fname = request.form.get('fname')
        current_user.lname = request.form.get('lname')
        current_user.email = request.form['email']
        current_user.postcode = request.form['postcode']
        current_user.address = request.form['address']
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('user_info_update.html')


@main.route('/use_points', methods=['GET', 'POST'])
@login_required
def use_points():
    total = current_user.loyalty_points

    # 1. Define 'using' with a default value at the start
    using = session.get('points_using', 0)

    if request.method == 'POST':
        using = request.form.get('name_of_slider')
        session['points_using'] = using
        session.modified = True

        flash(f"Applied {using} points!")
        return redirect(url_for('main.cart'))

    # 2. Now 'using' is guaranteed to exist here
    return render_template('loyalty_use.html', total=total, using=using)


if __name__ == '__main__':
    app.run(port=4242)
