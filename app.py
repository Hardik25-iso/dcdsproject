import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- APP INITIALIZATION ---
app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
DB_USER = 'root'
DB_PASSWORD = 'root'
DB_HOST = 'localhost'
DB_NAME = 'orphanage_db'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a-secret-key-you-should-change'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app) 

# --- LOGIN MANAGER SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    orphanage = db.relationship('Orphanage', back_populates='user', uselist=False)

class Orphanage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    items = db.relationship('ItemNeeded', back_populates='orphanage', cascade="all, delete-orphan")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    user = db.relationship('User', back_populates='orphanage')
    updates = db.relationship('Update', back_populates='orphanage', cascade="all, delete-orphan")

class ItemNeeded(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity_needed = db.Column(db.Integer, nullable=False)
    is_urgent = db.Column(db.Boolean, default=False, nullable=False)
    date_posted = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(20), default='Active')
    orphanage_id = db.Column(db.Integer, db.ForeignKey('orphanage.id'), nullable=False)
    orphanage = db.relationship('Orphanage', back_populates='items')
    pledged_by = db.Column(db.String(100), nullable=True)
    pledge_timestamp = db.Column(db.DateTime, nullable=True)

class Update(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    orphanage_id = db.Column(db.Integer, db.ForeignKey('orphanage.id'), nullable=False)
    orphanage = db.relationship('Orphanage', back_populates='updates')


# --- ROUTES ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/needs')
def needs_list():
    all_orphanages = Orphanage.query.all()
    return render_template('needs_list.html', orphanages=all_orphanages)

@app.route('/pledge/<int:item_id>', methods=['POST'])
def pledge(item_id):
    item_to_pledge = ItemNeeded.query.get_or_404(item_id)
    donor_name = request.form.get('donor_name')
    if item_to_pledge.status == 'Active' and donor_name:
        item_to_pledge.status = 'Pledged'
        item_to_pledge.pledged_by = donor_name
        item_to_pledge.pledge_timestamp = datetime.utcnow()
        db.session.commit()
    return redirect(url_for('needs_list'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(email=request.form['email'], password=hashed_password)
        new_orphanage = Orphanage(name=request.form['name'], city=request.form['city'], address=request.form['address'], contact_email=request.form['contact_email'], description=request.form['description'], user=new_user)
        db.session.add(new_user)
        db.session.add(new_orphanage)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- SECURE ORPHANAGE DASHBOARD ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        is_urgent = 'is_urgent' in request.form
        new_item = ItemNeeded(
            item_name=request.form['item_name'],
            category=request.form['category'],
            quantity_needed=request.form['quantity_needed'],
            is_urgent=is_urgent,
            orphanage_id=current_user.orphanage.id
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('admin/add_item.html')

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item_to_edit = ItemNeeded.query.get_or_404(item_id)
    if item_to_edit.orphanage.user != current_user:
        return "Unauthorized", 403
    if request.method == 'POST':
        item_to_edit.item_name = request.form['item_name']
        item_to_edit.category = request.form['category']
        item_to_edit.quantity_needed = request.form['quantity_needed']
        item_to_edit.status = request.form['status']
        item_to_edit.is_urgent = 'is_urgent' in request.form
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('admin/edit_item.html', item=item_to_edit)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item_to_delete = ItemNeeded.query.get_or_404(item_id)
    if item_to_delete.orphanage.user != current_user:
        return "Unauthorized", 403
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(url_for('dashboard'))

# New route for adding updates/thank you notes
@app.route('/add_update', methods=['GET', 'POST'])
@login_required
def add_update():
    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('body')
        
        if title and body:
            new_update = Update(
                title=title,
                body=body,
                orphanage_id=current_user.orphanage.id
            )
            db.session.add(new_update)
            db.session.commit()
            return redirect(url_for('dashboard'))
            
    # FIX: Corrected the path to the template
    return render_template('admin/add_update.html')

if __name__ == '__main__':
    app.run(debug=True)

