from flask import Flask, render_template,jsonify,request,redirect,url_for,session, send_file, render_template_string
from datetime import datetime
from werkzeug.security import generate_password_hash
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import generate_password_hash
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin,roles_required,login_required
from uuid import uuid4
from celery_worker import make_celery
import time
from celery.result import AsyncResult
from httplib2 import Http
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
# from celery.schedules import crontab


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['PROPAGATE_EXCEPTIONS'] = True  
app.config['SECURITY_PASSWORD_SALT'] = 'your-security-salt'
app.config['SECURITY_PASSWORD_SINGLE_HASH'] = True  # Default is True
app.config['DEBUG'] = True
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

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
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid4()))
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    role = db.Column(db.String(80), nullable=False, default='influencer')
    active = db.Column(db.Boolean(), nullable=False, default=True) 
    approve = db.Column(db.Boolean(), nullable=False, default=False) 


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    visibility = db.Column(db.String(50), nullable=False, default='public')  
    goals = db.Column(db.Text, nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sponsor = db.relationship('User', backref='campaigns')

    ad_requests = db.relationship('AdRequest', back_populates='campaign', lazy='dynamic')

class AdRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False) 
    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   
    messages = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    payment_amount = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pending')  

    campaign = db.relationship('Campaign', back_populates='ad_requests')
    influencer = db.relationship('User', backref=db.backref('ad_requests', lazy='dynamic'))

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)



def initialize_app(app):
    with app.app_context():
        db.create_all() 
        if not User.query.filter_by(name='admin').first():
            hashed_password = generate_password_hash('password').decode('utf-8')
            user = User(name='admin', password=hashed_password, role='admin',email='admin@example.com',active=True)
            db.session.add(user)
            db.session.commit()

initialize_app(app)


app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)

celery = make_celery(app) 

@celery.task()
def add_together(a, b):
    time.sleep(5)
    return a + b

@celery.task()
def generate_csv(user_id):
    import csv
    time.sleep(6)  

    campaigns = Campaign.query.filter_by(sponsor_id=user_id).all()
    fields = ["Campaign Name", "Description", "Start_Date", "End_Date", "Budget", "Visibility"]
    rows = []

    for campaign in campaigns:
        print(f"Processing campaign: {campaign.name}") 
        rows.append([
            campaign.name,
            campaign.description,
            campaign.start_date,
            campaign.end_date,
            campaign.budget,
            campaign.visibility
        ])
    print(rows)
    csv_file_path = "static/data.csv"
    with open(csv_file_path, "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(rows)

    return f"CSV file generated for user ID: {user_id}!"

@celery.task
def send_influencer_reminders():
    from json import dumps
    from datetime import datetime, timedelta
    WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAAWXGqUq8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=lJGSYURmKTV6C3DYMnUv3Nt0kYg6HUJn6MeMc0piHBk"

    url = WEBHOOK_URL
    influencers = User.query.filter_by(role="influencer", active=True).all()

    for influencer in influencers:
        pending_requests = AdRequest.query.filter_by(
            influencer_id=influencer.id, status='Pending'
        ).all()

        if not pending_requests:
            # No ad requests
            bot_message = {
                'text': f"Hello {influencer.name}, you have no ad requests yet. Check out public campaigns on our site!"
            }
        else:
            bot_message = {
                'text': f"Hello {influencer.name}, you have pending ad requests. Check them out on our site!"
            }

        # Send the message via the webhook
        message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
        http_obj = Http()
        response = http_obj.request(
            uri=url,
            method='POST',
            headers=message_headers,
            body=dumps(bot_message),
        )
        print(f"Response for {influencer.name}: {response}")

    return "Reminders are being sent successfully!"

SMPTP_SERVER_HOST="localhost"
SMPTP_SERVER_PORT=1025
SENDER_ADDRESS="admin@example.com"
SENDER_PASSWORD=""

# def send_email(to_address,subject,message,content="html",attachment_file=None):
#     msg=MIMEMultipart()
#     msg["From"]=SENDER_ADDRESS
#     msg["To"]=to_address
#     msg["Subject"]=subject
#     if content=="html":      
#         msg.attach(MIMEText(message,"html"))
#     else:
#         msg.attach(MIMEText(message,"plain"))
        
#     if attachment_file:
#         with open(attachment_file,"rb") as attachment:
            
#             part =MIMEBase("application","octet-stream")
#             part.set_payload(attachment.read())
#             encoders.encode_base64(part)


#     s=smtplib.SMTP(host=SMPTP_SERVER_HOST,port=SMPTP_SERVER_PORT)
#     s.login(SENDER_ADDRESS,SENDER_PASSWORD)
#     s.send_message(msg)
#     s.quit()
#     return True
def send_email(to_address, subject, message, content="html", attachment_file=None):
    msg = MIMEMultipart()
    msg["From"] = SENDER_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = subject

    # Attach the email body based on the content type
    if content == "html":
        msg.attach(MIMEText(message, "html"))  # Use 'html' type for rendering HTML content
    else:
        msg.attach(MIMEText(message, "plain"))  # Use 'plain' type for plain text

    # Add attachment if provided
    if attachment_file:
        with open(attachment_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            # part.add_header(
            #     "Content-Disposition",
            #     f"attachment; filename={attachment_file.split('/')[-1]}",
            # )
            msg.attach(part)

    # Send the email using SMTP
    s = smtplib.SMTP(host=SMPTP_SERVER_HOST, port=SMPTP_SERVER_PORT)
    s.login(SENDER_ADDRESS, SENDER_PASSWORD)
    s.send_message(msg)
    s.quit()

    return True


@celery.task()
def send_reminer_via_email():
    all_users = User.query.all()

    for user in all_users:
        campaigns = Campaign.query.filter_by(sponsor_id=user.id).all()
        if campaigns:
            email_content = render_template_string(
                """
                    <html>
                    <head>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                            }
                            h2 {
                                color: #333;
                            }
                            ul {
                                list-style-type: none;
                                padding: 0;
                            }
                            li {
                                margin-bottom: 10px;
                            }
                        </style>
                    </head>
                    <body>
                        <h2>Your Recent Campaign Details</h2>
                        <p>Hello {{ user.name }},</p>
                        <p>Here are your recent campaigns:</p>
                        <ul>
                            {% for campaign in campaigns %}
                                <li>
                                    <strong>Campaign ID:</strong> {{ campaign.id }}<br>
                                    <strong>Campaign Name:</strong> {{ campaign.name }}<br>
                                    <strong>Start Date:</strong> {{ campaign.start_date }}<br>
                                    <strong>End Date:</strong> {{ campaign.end_date }}<br>
                                    <strong>Visibility:</strong> {{ campaign.visibility }}
                                    <strong>Budget:</strong> {{ campaign.budget }}
                                </li>
                                <br>
                            {% endfor %}
                        </ul>
                    </body>
                    </html>
                """,
                user=user,
                campaigns=campaigns,
            )

            send_email(
                to_address=user.email,
                subject="Your Recent Campaign Details",
                message=email_content,
                content="html",
            )
    
    return "Reminder emails sent successfully"




# @celery.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(10.0, send_influencer_reminders.s(), name='reminder sended')

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        20,
        send_reminer_via_email.s(),
        name='send_reminder_every_20_seconds',
    )


@app.route("/trigger-celery-job")
def trigger_celery_job():
    user_id = session["user_id"]
    a=generate_csv.delay(user_id)
    return{
        "Task_id":a.id,
        "Task_state":a.state,
        "Task_result":a.result
    }

@app.route("/status/<int:id>")
def check_status(id):
    res=AsyncResult(id)
    return{
        "Task_id":res.id,
        "Task_state":res.state,
        "Task_result":res.result
    }

@app.route("/download-file")
def download_file():
    time.sleep(5)
    return send_file("static/data.csv")

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

@app.route('/api/campaigns')
def api_campaigns():
    campaigns = Campaign.query.all()
    campaigns_list = [
        {
            'id': campaign.id,
            'name': campaign.name,
            'description': campaign.description,
            'start_date': campaign.start_date.strftime('%Y-%m-%d'),
            'end_date': campaign.end_date.strftime('%Y-%m-%d'),
            'budget': campaign.budget,
            'visibility': campaign.visibility,
            'goals': campaign.goals
        }
        for campaign in campaigns
    ]
    return jsonify(campaigns_list)


@app.route('/api/create_campaign', methods=['POST'])
def create_campaign():
    data = request.get_json()
    try:
        new_campaign = Campaign(
            name=data['name'],
            description=data.get('description'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d'),
            budget=data['budget'],
            visibility=data.get('visibility', 'public'),
            goals=data.get('goals')
        )
        db.session.add(new_campaign)
        db.session.commit()
        return jsonify({'message': 'Campaign created successfully!'}), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create campaign: {str(e)}'}), 400

@app.route('/api/ad_requests')
def api_ad_requests():
    # Query all ad requests and convert them to a dictionary or list format
    ad_requests = AdRequest.query.all()
    # Convert ad request objects into a list of dictionaries for JSON serialization
    ad_requests_list = [
        {
            'id': ad_request.id,
            'title': ad_request.title,
            'description': ad_request.description,
            'status': ad_request.status
            # Include other fields as necessary
        }
        for ad_request in ad_requests
    ]
    return jsonify(ad_requests_list)


# API Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    name = data.get('name')
    password = data.get('password')
    role = data.get('role', 'influencer')
    email= data.get('email')
    approve=False

    if not name or not password or not role:
        return jsonify({"error": "Name, password, and role are required"}), 400

    existing_user = User.query.filter_by(name=name).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    hashed_password = generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, password=hashed_password, role=role,email=email,approve=approve)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "User registered successfully"}), 201


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

    if user.role =='influencer' or user.role == 'admin':
        if user and user.verify_and_update_password(password):
            role_list = [role.name for role in user.roles] if user.roles else [user.role]
            session['user_id'] = user.id
            session['role'] = role_list[0]  
            print(session['user_id'])

            return jsonify({
                'success': True,
                'user_id': user.id,
                'user_name': user.name,
                'role': role_list
            })
    else:
        if user.approve==True:
            if user and user.verify_and_update_password(password):
                role_list = [role.name for role in user.roles] if user.roles else [user.role]
                session['user_id'] = user.id
                session['role'] = role_list[0] 
                print(session['user_id'])

                return jsonify({
                    'success': True,
                    'user_id': user.id,
                    'user_name': user.name,
                    'role': role_list
                })
        else:
            return jsonify({'success': False, 'error': 'User is not approved yet'}), 401
            


    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@app.before_request
def clear_stale_session():
    # If there's no user ID in the session, clear the session
    if 'user_id' not in session:
        session.clear()

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()  # Clears all session data
    return jsonify({'success': True, 'message': 'Logged out successfully'})



@app.route('/debug/session', methods=['GET'])
def debug_session():
    return jsonify(dict(session))  # View current session data

@app.route('/debug/clear-session', methods=['GET'])
def clear_session_debug():
    session.clear()
    return "Session cleared!", 200

@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if 'user_id' not in session or 'role' not in session:
        return jsonify({'error': 'Unauthorized'}), 401  

    user = User.query.get(session['user_id'])

    if not user or user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403 

    users = User.query.all()
    users_data = [
        {
            'id': u.id,
            'name': u.name,
            'role': u.role
        } for u in users
    ]
    sponsors = User.query.filter(User.role == "sponsor", User.approve == False).all()

    sponsors_data = [
        {
            "id": sponsor.id,
            "name": sponsor.name,
            "email": sponsor.email
        } for sponsor in sponsors]

    campaigns = Campaign.query.all()
    campaigns_data = [
        {
            'id': c.id,
            'name': c.name,
            'visibility': c.visibility,
            'start_date': c.start_date.strftime('%Y-%m-%d'),
            'end_date': c.end_date.strftime('%Y-%m-%d'),
            'budget': c.budget,
            'goals': c.goals
        } for c in campaigns
    ]

    ad_requests = AdRequest.query.all()
    ad_requests_data = [
        {
            'id': ar.id,
            'requirements': ar.requirements,
            'payment_amount': ar.payment_amount,
            'status': ar.status,
            'campaign': {
                'id': ar.campaign.id,
                'name': ar.campaign.name,
            },
            'influencer': {
                'id': ar.influencer.id,
                'name': ar.influencer.name,
            }
        } for ar in ad_requests
    ]

    return jsonify({
        'users': users_data,
        'campaigns': campaigns_data,
        'ad_requests': ad_requests_data,
        'sponsors': sponsors_data,
    })

@app.route("/approve_sponsor/<int:user_id>", methods=["PATCH"])
def approve_sponsor(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user.role != "sponsor":
            return jsonify({"error": "User is not a sponsor"}), 400
        
        user.approve = True
        db.session.commit()
        return jsonify({"message": "Sponsor approved successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/sponsor_dashboard", methods=["GET", "POST"])
def sponsor_dashboard():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return 401 if user is not logged in

    user_id = session['user_id']  # Get the sponsor's user ID from the session
    user = User.query.get(user_id)

    if not user or user.role != 'sponsor':
        return jsonify({'error': 'Access denied. Only sponsors can access this page.'}), 403  # Return 403 if not a sponsor

    if request.method == 'POST':
        # Handle campaign creation
        try:
            data = request.get_json()  # Parse JSON data
            name = data.get('name')
            description = data.get('description')
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
            budget = float(data.get('budget'))
            visibility = data.get('visibility')
            goals = data.get('goals')

            new_campaign = Campaign(
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                budget=budget,
                visibility=visibility,
                goals=goals,
                sponsor_id=user_id
            )

            db.session.add(new_campaign)
            db.session.commit()

            return jsonify({'message': 'Campaign created successfully'}), 201
        except Exception as e:
            return jsonify({'error': f'Failed to create campaign: {str(e)}'}), 400

    # Handle GET request
    search_query = request.args.get('search_query', '')
    if search_query:
        search_results = User.query.filter(
            User.role == 'influencer',
            User.name.ilike(f'%{search_query}%')
        ).all()
    else:
        search_results = []

    influencers = User.query.filter_by(role='influencer').all()
    campaigns = Campaign.query.filter_by(sponsor_id=user_id).all()

    # Fetch ad requests related to the sponsor's campaigns
    campaign_ids = [campaign.id for campaign in campaigns]
    ad_requests = AdRequest.query.filter(AdRequest.campaign_id.in_(campaign_ids)).all()

    # Prepare data for JSON response
    campaigns_data = [{
        'id': campaign.id,
        'name': campaign.name,
        'description': campaign.description,
        'start_date': campaign.start_date.strftime('%Y-%m-%d'),
        'end_date': campaign.end_date.strftime('%Y-%m-%d'),
        'budget': campaign.budget,
        'visibility': campaign.visibility,
        'goals': campaign.goals
    } for campaign in campaigns]

    influencers_data = [{
        'id': influencer.id,
        'name': influencer.name
    } for influencer in influencers]

    search_results_data = [{
        'id': influencer.id,
        'name': influencer.name
    } for influencer in search_results]

    ad_requests_data = [{
        'id': ad_request.id,
        'requirements': ad_request.requirements,
        'payment_amount': ad_request.payment_amount,
        'status': ad_request.status,
        'campaign_id': ad_request.campaign_id,
        'influencer_id': ad_request.influencer_id
    } for ad_request in ad_requests]

    return jsonify({
        'user': user.name,
        'campaigns': campaigns_data,
        'influencers': influencers_data,
        'ad_requests': ad_requests_data,
        'search_results': search_results_data
    })

@app.route('/influencer/dashboard', methods=["GET", "POST"])
def influencer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    user_id = session['user_id']  # Retrieve the user ID from the session
    user = User.query.get(user_id)

    if not user or user.role != 'influencer':
        return redirect(url_for('index'))  # Redirect if not an influencer or user doesn't exist

    # Fetch ad requests where the influencer_id matches the logged-in user's ID
    ad_requests = AdRequest.query.filter_by(influencer_id=user_id).all()
    public_campaigns = Campaign.query.filter_by(visibility="public").all()

    # Prepare the ad request data
    ad_requests_data = [
        {
            'id': ad.id,
            'requirements': ad.requirements or '',
            'payment_amount': ad.payment_amount or 0.0,
            'status': ad.status or 'Pending',
            'messages': ad.messages or '',
            'campaign': {
                'id': ad.campaign.id if ad.campaign else None,
                'name': ad.campaign.name if ad.campaign else 'N/A',
                'visibility': ad.campaign.visibility if ad.campaign else 'N/A',
            }
        }
        for ad in ad_requests
    ]

    # Prepare the public campaign data
    public_campaigns_data = [
        {
            'id': camp.id,
            'name': camp.name,
            'description': camp.description,
            'budget': camp.budget,
            'start_date': camp.start_date.isoformat(),
            'end_date': camp.end_date.isoformat(),
        }
        for camp in public_campaigns
    ]

    return jsonify({
        'user': user.name,
        'ad_requests': ad_requests_data,
        'public_campaigns': public_campaigns_data
    })



@app.route('/search_campaigns', methods=['GET'])
def search_campaigns():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return an error if user is not logged in

    user_id = session['user_id']  # Retrieve the user ID from the session

    # Get search parameters from the query string
    name = request.args.get('name')
    budget = request.args.get('budget', type=float)

    # Base query: search for public campaigns
    query = Campaign.query.filter_by(visibility='public')

    # Add filters based on search parameters
    if name:
        query = query.filter(Campaign.name.ilike(f'%{name}%'))
    if budget is not None:
        query = query.filter(Campaign.budget <= budget)

    # Execute the query and get results
    campaigns = query.all()

    # Prepare the data for the JSON response
    campaigns_data = [{
        'id': campaign.id,
        'name': campaign.name,
        'description': campaign.description,
        'budget': campaign.budget,
        'start_date': campaign.start_date,
        'end_date': campaign.end_date,
        'visibility': campaign.visibility
    } for campaign in campaigns]

    return jsonify({'campaigns': campaigns_data})
    
@app.route("/update_ad_request_status", methods=["POST"])
def update_ad_request_status():
    try:
        data = request.get_json()  # Parse JSON payload
        ad_request_id = data.get("ad_request_id")
        status = data.get("status")

        # Validate inputs
        if not ad_request_id or not status:
            return jsonify({"error": "Ad request ID and status are required."}), 400

        # Fetch the ad request
        ad_request = AdRequest.query.get(ad_request_id)
        if not ad_request:
            return jsonify({"error": "Ad request not found."}), 404

        # Update the status
        ad_request.status = status
        db.session.commit()

        return jsonify({
            "message": f"Ad request status updated to {status}.",
            "status": "success",
            "ad_request_id": ad_request_id
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/create_adreq", methods=["GET", "POST"])
def create_adreq():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return 401 if user is not logged in

    if request.method == "POST":
        # Parse JSON data from the request
        data = request.get_json()
        requirements = data.get('requirements')
        payment_amount = data.get('payment_amount')
        campaign_id = data.get('campaign_id')
        influencer_id = data.get('influencer_id')

        # Validate required fields
        if not all([requirements, payment_amount, campaign_id, influencer_id]):
            return jsonify({'error': 'Missing required fields'}), 400  # Return 400 if data is missing

        try:
            # Create a new AdRequest object
            new_ad_request = AdRequest(
                requirements=requirements,
                payment_amount=float(payment_amount),
                status="Pending",  # Default status is "Pending"
                campaign_id=int(campaign_id),
                influencer_id=int(influencer_id)
            )

            # Add the ad request to the database
            db.session.add(new_ad_request)
            db.session.commit()

            return jsonify({
                'message': 'Ad request created successfully',
                'ad_request': {
                    'id': new_ad_request.id,
                    'requirements': new_ad_request.requirements,
                    'payment_amount': new_ad_request.payment_amount,
                    'status': new_ad_request.status,
                    'campaign_id': new_ad_request.campaign_id,
                    'influencer_id': new_ad_request.influencer_id
                }
            }), 201  # Return 201 Created
        except Exception as e:
            return jsonify({'error': str(e)}), 500  # Handle unexpected errors

    # Handle GET request: Fetch all campaigns and influencers
    campaigns = Campaign.query.all()
    influencers = User.query.filter_by(role='Influencer').all()

    # Prepare data for JSON response
    campaigns_data = [{
        'id': campaign.id,
        'name': campaign.name,
        'description': campaign.description,
        'budget': campaign.budget,
        'visibility': campaign.visibility
    } for campaign in campaigns]

    influencers_data = [{
        'id': influencer.id,
        'name': influencer.name
    } for influencer in influencers]

    return jsonify({
        'campaigns': campaigns_data,
        'influencers': influencers_data
    })

@app.route("/accept_sp", methods=["POST"])
def accept_sp():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return 401 if user is not logged in

    data = request.get_json()  # Parse JSON data from the request
    ad_req_id = data.get("ad_request_id")
    status = data.get("status")
    new_amount = data.get("new_amount")

    if not ad_req_id or not status or not new_amount:
        return jsonify({'error': 'Missing required fields'}), 400  # Return 400 if data is incomplete

    # Query the ad_request by ID
    ad_request = AdRequest.query.get(ad_req_id)

    if ad_request:
        # Update the status and payment amount of the ad_request
        ad_request.status = status
        ad_request.payment_amount = float(new_amount)

        # Save the changes to the database
        db.session.commit()

        return jsonify({
            'message': f'Ad request {ad_req_id} status updated to {status}.',
            'ad_request': {
                'id': ad_request.id,
                'status': ad_request.status,
                'payment_amount': ad_request.payment_amount,
                'campaign_id': ad_request.campaign_id,
                'influencer_id': ad_request.influencer_id
            }
        }), 200
    else:
        return jsonify({'error': f'Ad request with ID {ad_req_id} not found.'}), 404

@app.route("/reject_sp", methods=["POST"])
def reject_sp():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return 401 if user is not logged in

    data = request.get_json()  # Parse JSON data from the request
    ad_req_id = data.get("ad_request_id")
    status = data.get("status")

    if not ad_req_id or not status:
        return jsonify({'error': 'Missing required fields'}), 400  # Return 400 if data is incomplete

    # Query the ad_request by ID
    ad_request = AdRequest.query.get(ad_req_id)

    if ad_request:
        # Update the status of the ad_request
        ad_request.status = status

        # Save the changes to the database
        db.session.commit()

        return jsonify({
            'message': f'Ad request {ad_req_id} status updated to {status}.',
            'ad_request': {
                'id': ad_request.id,
                'status': ad_request.status,
                'campaign_id': ad_request.campaign_id,
                'influencer_id': ad_request.influencer_id
            }
        }), 200
    else:
        return jsonify({'error': f'Ad request with ID {ad_req_id} not found.'}), 404

@app.route("/search_influencers", methods=["GET"])
def search_influencers():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return 401 if user is not logged in

    # Get the search query parameter
    search_query = request.args.get('query', '').strip()

    if not search_query:
        return jsonify({'error': 'Search query is required'}), 400  # Return 400 if no query is provided

    try:
        # Search for influencers whose name matches the query
        influencers = User.query.filter(
            User.role == 'influencer',
            User.name.ilike(f'%{search_query}%')
        ).all()

        # Prepare the response data
        influencers_data = [{
            'id': influencer.id,
            'name': influencer.name
        } for influencer in influencers]

        return jsonify({'influencers': influencers_data}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred while searching for influencers: {str(e)}'}), 500
    

@app.route('/update_campaign/<int:id>', methods=["POST"])
def update_campaign(id):
    campaign = Campaign.query.get(id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404  # Return error if not found

    try:
        # Extract data from request
        data = request.get_json()
        campaign.name = data.get('name', campaign.name)
        campaign.description = data.get('description', campaign.description)
        campaign.start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
        campaign.end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
        campaign.budget = float(data.get('budget', campaign.budget))
        campaign.visibility = data.get('visibility', campaign.visibility)
        campaign.goals = data.get('goals', campaign.goals)

        # Save changes
        db.session.commit()

        # Return updated campaign data
        return jsonify({
            'message': 'Campaign updated successfully!',
            'campaign': {
                'id': campaign.id,
                'name': campaign.name,
                'description': campaign.description,
                'start_date': campaign.start_date.strftime('%Y-%m-%d'),
                'end_date': campaign.end_date.strftime('%Y-%m-%d'),
                'budget': campaign.budget,
                'visibility': campaign.visibility,
                'goals': campaign.goals
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update campaign: {str(e)}'}), 400


@app.route('/delete_campaign/<int:id>', methods=['POST'])
def delete_campaign(id):
    campaign = Campaign.query.get(id)
    
    if campaign:
        # Delete associated ad requests
        ad_req = AdRequest.query.filter_by(campaign_id=id).all()
        if ad_req:
            for req in ad_req:
                db.session.delete(req)
                db.session.commit()

        # Delete the campaign
        db.session.delete(campaign)
        db.session.commit()

        # Return success response
        return jsonify({
            'message': 'Campaign deleted successfully!',
            'status': 'success'
        }), 200  # HTTP status code for OK
    else:
        # Return failure response if campaign not found
        return jsonify({
            'message': 'Campaign not found.',
            'status': 'error'
        }), 404  # HTTP status code for Not Found

@app.route('/delete_ad_request/<int:id>', methods=['POST'])
def delete_ad_request(id):
    ad_request = AdRequest.query.get(id)
    
    if ad_request:
        db.session.delete(ad_request)
        db.session.commit()
        return jsonify({
            'message': 'Ad request deleted successfully!',
            'status': 'success'
        }), 200
    else:
        return jsonify({
            'message': 'Ad request not found.',
            'status': 'error'
        }), 404

@app.route('/update_ad_request/<int:id>', methods=["POST"])
def update_ad_request(id):
    ad_request = AdRequest.query.get(id)
    if not ad_request:
        return jsonify({'error': 'Ad request not found'}), 404  # Return error if not found

    try:
        # Extract data from the request
        data = request.get_json()
        ad_request.requirements = data.get('requirements', ad_request.requirements)
        ad_request.payment_amount = float(data.get('payment_amount', ad_request.payment_amount))
        ad_request.status = data.get('status', ad_request.status)

        # Save changes to the database
        db.session.commit()

        # Return updated ad request data
        return jsonify({
            'message': 'Ad request updated successfully!',
            'ad_request': {
                'id': ad_request.id,
                'requirements': ad_request.requirements,
                'payment_amount': ad_request.payment_amount,
                'status': ad_request.status,
                'campaign_id': ad_request.campaign_id,
                'influencer_id': ad_request.influencer_id
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update ad request: {str(e)}'}), 400
    
@app.route('/delete_campaignadmin/<int:id>', methods=['DELETE'])
def delete_campaignadmin(id):
    campaign = Campaign.query.get(id)
    if not campaign:
        return jsonify({'message': 'Campaign not found.', 'status': 'error'}), 404

    # Delete related ad requests
    ad_requests = AdRequest.query.filter_by(campaign_id=id).all()
    for req in ad_requests:
        db.session.delete(req)
    
    db.session.delete(campaign)
    db.session.commit()

    return jsonify({'message': 'Campaign and related ad requests deleted successfully!', 'status': 'success'}), 200

@app.route('/delete_adrequest/<int:id>', methods=['DELETE'])
def delete_adrequest(id):
    ad_request = AdRequest.query.get(id)
    if not ad_request:
        return jsonify({'message': 'Ad request not found.', 'status': 'error'}), 404

    db.session.delete(ad_request)
    db.session.commit()

    return jsonify({'message': 'Ad request deleted successfully!', 'status': 'success'}), 200



@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    thisuser = User.query.get(user_id)
    if not thisuser:
        return jsonify({'message': 'User not found.', 'status': 'error'}), 404

    if thisuser.role == "Admin":
        return jsonify({'message': 'Admin users cannot be deleted.', 'status': 'error'}), 403

    # Delete related campaigns and their ad requests if the user is a sponsor
    camp_list = Campaign.query.filter_by(sponsor_id=thisuser.id).all()
    for camp in camp_list:
        ad_req_list = AdRequest.query.filter_by(campaign_id=camp.id).all()
        for ad_req in ad_req_list:
            db.session.delete(ad_req)
        db.session.delete(camp)

    # Delete ad requests where the user is an influencer
    ad_req_list = AdRequest.query.filter_by(influencer_id=thisuser.id).all()
    for ad_req in ad_req_list:
        db.session.delete(ad_req)

    # Delete the user
    db.session.delete(thisuser)
    db.session.commit()

    return jsonify({'message': 'User and associated data deleted successfully.', 'status': 'success'}), 200  

if __name__ == '__main__':
    app.run(debug=True)
