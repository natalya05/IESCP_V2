# app.py
from flask import Flask, render_template,jsonify,request,redirect,url_for,session
# from models import User as UserModel, db, Role

# from flask_security import Security, SQLAlchemyUserDatastore,roles_required, roles_accepted, login_required, UserMixin, RoleMixin
# from api.resource import api, User


from werkzeug.security import generate_password_hash

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import generate_password_hash
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin,roles_required,login_required
from uuid import uuid4

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['PROPAGATE_EXCEPTIONS'] = True  
app.config['SECURITY_PASSWORD_SALT'] = 'your-security-salt'

app.config['SECURITY_PASSWORD_SINGLE_HASH'] = True  # Default is True
app.config['DEBUG'] = True
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)

# Define models
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid4()))
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    role = db.Column(db.String(80), nullable=False, default='influencer')

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

def initialize_app(app):
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(name='admin').first():
            user_datastore.create_user(name='admin', password='password')
            db.session.commit()

initialize_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/message')
def get_message():
    data = {
        'message': 'Hello from Flask JSON API!',
        'status': 'success'
    }
    return jsonify(data)

# @app.route('/campaigns')
# def campaigns():
#     campaigns = Campaign.query.all()
#     return render_template('campaign.html', campaigns=campaigns)

# @app.route('/api/campaigns')
# def api_campaigns():
#     # Query all campaigns and convert them to a dictionary or list format
#     campaigns = Campaign.query.all()
#     # Convert campaign objects into a list of dictionaries for JSON serialization
#     campaigns_list = [
#         {
#             'id': campaign.id,
#             'name': campaign.name,
#             'description': campaign.description
#             # Include other fields as necessary
#         }
#         for campaign in campaigns
#     ]
#     return jsonify(campaigns_list)

# @app.route('/ad_requests')
# def ad_requests():
#     ad_requests = AdRequest.query.all()
#     return render_template('ad_request.html', ad_requests=ad_requests)

# @app.route('/api/ad_requests')
# def api_ad_requests():
#     # Query all ad requests and convert them to a dictionary or list format
#     ad_requests = AdRequest.query.all()
#     # Convert ad request objects into a list of dictionaries for JSON serialization
#     ad_requests_list = [
#         {
#             'id': ad_request.id,
#             'title': ad_request.title,
#             'description': ad_request.description,
#             'status': ad_request.status
#             # Include other fields as necessary
#         }
#         for ad_request in ad_requests
#     ]
#     return jsonify(ad_requests_list)


# API Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    name = data.get('name')
    password = data.get('password')
    role = data.get('role', 'influencer')

    if not name or not password or not role:
        return jsonify({"error": "Name, password, and role are required"}), 400

    existing_user = User.query.filter_by(name=name).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    hashed_password = generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, password=hashed_password, role=role)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "User registered successfully"}), 201


# @app.route('/api/login', methods=['POST'])
# def api_login():
#     name = request.json.get('name')
#     password = request.json.get('password')

#     user = User.query.filter_by(name=name).first()

#     if user and user.verify_and_update_password(password):
#         role_list = [role.name for role in user.roles] if user.roles else [user.role]
#         role = role_list[0]

#         session['user_id'] = user.id
#         session['role'] = role

#         return jsonify({
#             'success': True,
#             'user_id': user.id,
#             'user_name': user.name,
#             'role': role_list
#         })

#     return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@app.route('/api/user-role', methods=['GET'])
def get_user_role():
    if 'user_id' not in session or 'role' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    return jsonify({'role': session['role']})


@app.route('/api/login', methods=['POST'])
def api_login():
    name = request.json.get('name')
    password = request.json.get('password')

    user = User.query.filter_by(name=name).first()

    if user and user.verify_and_update_password(password):
        role_list = [role.name for role in user.roles] if user.roles else [user.role]
        session['user_id'] = user.id
        session['role'] = role_list[0]  # Store role in session

        return jsonify({
            'success': True,
            'user_id': user.id,
            'user_name': user.name,
            'role': role_list
        })

    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401





@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# New logout route that returns a JSON response
@app.route('/api/logout')
def api_logout():
    session.clear()  # Clears the session data
    return jsonify({'success': True, 'message': 'You have been logged out successfully.'})


@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():

    print("Session data:", session)
    if 'user_id' not in session or 'role' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])

    if not user or 'Admin' not in [role.name for role in user.roles]:
        return redirect(url_for('index'))  # Redirect unauthorized users

    return jsonify({
        'message': f'Welcome, Admin {user.name}',
        'data': 'Admin-specific dashboard data here...'
    })

# @app.route('/sponsor/dashboard', methods=['GET'])
# def sponsor_dashboard():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     user = User.query.get(session['user_id'])
#     if not user or 'Sponsor' not in [role.name for role in user.roles]:
#         return redirect(url_for('index'))  # Redirect unauthorized users

#     campaigns = Campaign.query.filter_by(sponsor_id=user.id).all()
#     campaign_list = [{'id': c.id, 'name': c.name, 'budget': c.budget} for c in campaigns]

#     return jsonify({
#         'message': f'Welcome, Sponsor {user.name}',
#         'campaigns': campaign_list
#     })

# @app.route('/influencer/dashboard', methods=['GET'])
# def influencer_dashboard():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))

#     user = User.query.get(session['user_id'])
#     if not user or 'Influencer' not in [role.name for role in user.roles]:
#         return redirect(url_for('index'))  # Redirect unauthorized users

#     applied_campaigns = AdRequest.query.filter_by(user_id=user.id).all()
#     campaign_list = [{'id': c.id, 'name': c.campaign.name, 'status': c.status} for c in applied_campaigns]

#     return jsonify({
#         'message': f'Welcome, Influencer {user.name}',
#         'applied_campaigns': campaign_list
#     })




if __name__ == '__main__':
    app.run(debug=True)
