import json
import os
import datetime
from datetime import datetime
from flask import Flask, jsonify, render_template, request,redirect, send_from_directory, session, url_for
from request_handler import RequestHandler
from flask_cors import CORS
from flask_session import Session


COOKIE_NAME = 'Beautiful-Cookie'


# Create a Flask application
app = Flask(__name__)
# Generate a random secret key
secret_key = os.urandom(32)
print(secret_key.hex())
app.config['SECRET_KEY'] = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

handler = RequestHandler()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET'])
def sign_up():
     return render_template('SignUp.html')

# Define a route for handling POST requests
@app.route('/signup', methods=['POST'])
def signup():
    print(f'The submitted data is: {request.form}')
    handler.handle_signup(request.form)
    # Check if the account type is לקוחה (customer)
    successful_login, cookie = handler.handle_signup_cookie(request.form)
    if successful_login:
        print(f'cookie = {cookie}')
        response = redirect(url_for('dashboard'))  # Redirect to the dashboard
        response.set_cookie(COOKIE_NAME, cookie)
        print(f'signup: response = {response.headers},{response.data}')
        return response
    else:
        # If credentials are incorrect, return an error message
        error_message = "שם המשתמש או הסיסמא לא נכונים"
        return jsonify(success=False, error_message=error_message), 400
    
    

@app.route('/make-appointment', methods=['GET'])
def make_appointment():
     cookie = request.cookies.get(COOKIE_NAME)
     user_first_name, user_last_name, user_account_type, account_id = handler.handle_get_first_and_last_name(cookie)
     # build dict of [date]->([time]->employees)
     appointments_by_date = handler.handle_list_available_appointments()
     print('make_appointment: appointments_by_date: ', appointments_by_date)
     appointments_by_date_json = json.dumps({
         k.strftime('%d-%m-%Y'):v for k,v in appointments_by_date.items()
     })
     return render_template('make-appointment.html', appointments_by_date=appointments_by_date_json, account_id=account_id)

@app.route('/navbar', methods=['GET'])
def show_navbar():
    try:
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_account_type, account_id = handler.handle_get_first_and_last_name(cookie)
        print(f'The user details: {user_first_name} {user_last_name}, The account id:{account_id}')
        unread_notification_count = handler.handle_get_unread_notification_count(account_id) 
        return render_template('navbar.html', user_first_name=user_first_name, user_last_name=user_last_name,user_account_type=user_account_type, unread_notification_count=unread_notification_count)
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
    return "An error occurred while getting user info", 500

# Route to handle the forum page
@app.route('/forum', methods=['GET'])
def forum():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    # Fetch subjects from the database
    subjects = handler.handle_list_subjects()
    # print (f'subjects: {subjects}')
    return render_template('forum.html', subjects=subjects,account_id=account_id)

# Route to handle the forum page
@app.route('/manager-forum', methods=['GET'])
def manager_forum():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    # Fetch subjects from the database
    subjects = handler.handle_list_manager_subjects()
    # print (f'subjects: {subjects}')
    return render_template('manager-forum.html', subjects=subjects,account_id=account_id)

@app.route('/approve-subject', methods=['POST'])
def approve_subject():
    try:
        subject_id=request.json.get('subject_id')
        print('subject_id: ',subject_id)
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # approve the subject from the database
        handler.approve_subject(subject_id)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to delete this subject.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-subject', methods=['POST'])
def delete_subject():
    try:
        subject_id=request.json.get('subject_id')
        print('subject_id: ',subject_id)
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # Delete the subject from the database
        handler.delete_subject(subject_id)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to delete this subject.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/show-comments')
def list_comments():
    subject_id = request.args.get('subject_id')
    # Fetch comments related to the subject_id from the database
    comments = handler.handle_list_comments(subject_id)
    return jsonify(comments=comments)

@app.route('/submit-comment', methods=['POST'])
def submit_comment():
    #TODO: add the account id related to that comment
    handler.handle_submit_comment(request.form)
    # print(f"Comment added for subject ID {subject_id}: {content}")
    return jsonify(message='Comment added successfully')

@app.route('/login', methods=['POST'])
def login():
    print(f'The submitted data: {request.json}')
     # Call the handler to get the first and last names
    # first_name, last_name, email, account_id = handler.handle_get_first_and_last_name(request.json)
    successful_login, cookie = handler.handle_login(request.json)
    if successful_login:
        print(f'cookie = {cookie}')
        # TODO: url_for(make-appointment)
        response = jsonify(success=True, redirect_url=url_for('dashboard'))
        response.set_cookie(COOKIE_NAME, cookie)
        print(f'login: response = {response.headers},{response.data}')
        return response
    else:
        # If credentials are incorrect, return an error message
        error_message = "שם המשתמש או הסיסמא לא נכונים"
        return jsonify(success=False, error_message=error_message), 400
    
@app.route('/logout')
def logout():
    cookie = request.cookies.get(COOKIE_NAME)
    # TODO: return indicative result to user
    response = redirect(url_for('index'))
    try:
        handler.handle_logout(cookie)
        response.delete_cookie(COOKIE_NAME)
    except KeyError as e:
        print(f'Logout error: cookie {cookie} does not exist')
    
    return response # Redirect the user to the signin page


@app.route('/create-subject', methods=['GET'])
def createSubject():
     return render_template('create-subject.html')

@app.route('/create-subject', methods=['POST'])
def create_subject():
    print(f'create_subject: {request.json}')

    try:
        cookie = request.cookies.get(COOKIE_NAME)
        handler.handle_create_subject(request.json, cookie)
        
        # Redirect or return a success message as needed
        print(f'The submitted data is: {request.json}')
        return redirect(url_for('forum'))
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
        return "An error occurred while creating the subject", 500
    
@app.route('/add-work-constraints', methods=['POST'])
def add_work_constraints():
    print(f'add_work_constraints: {request.form}')

    try:
        cookie = request.cookies.get(COOKIE_NAME)
        handler.handle_add_work_constraints(request.form, cookie)
        print(f'added worj constraints to sql table')
       # Redirect or return a success message as needed
        return redirect(url_for('my_work_constraints'))
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
        return "An error occurred while submitting work constraints", 500
    
@app.route('/Work-constraints', methods=['GET'])
def my_work_constraints():
    print(f'starting work-constraints')
    try:
        cookie = request.cookies.get(COOKIE_NAME)
        constraints = handler.handle_get_work_constraints(cookie)
        print(f'constraints: ',constraints)
        return render_template('Work-constraints.html', constraints=constraints)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
        return "An error occurred while retrieving work constraints", 500
    
@app.route('/delete-constraint/<constraint_id>', methods=['POST'])
def delete_constraint(constraint_id):
    try:
        handler.handle_delete_work_constraint(constraint_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'error': 'Failed to delete constraint'}), 500
    
@app.route('/manager-appointment')
def get_work_constraints():
    try:
         # Retrieve list of employees from the database
        employees = handler.handle_get_employees()
        # Retrieve work constraints for each employee from the database
        constraints = handler.handle_get_work_constraints_for_all_employees()
        print(f'get work constraints: constraints: ', constraints, employees)
        return render_template('manager-appointment.html', constraints=constraints, employees=employees)
    except Exception as e:
        # Handle errors and return an appropriate response
        print(f"An error occurred: {str(e)}")
        return "An error occurred while retrieving work constraints", 500

# Define route to get employees
@app.route('/get-employees')
def get_employees():
    # Fetch employees from the database
    # Replace this with your database query to fetch employees
    employees = handler.handle_get_employees()
    return jsonify(employees)

@app.route('/save-work-schedule', methods=['POST'])
def save_work_schedule():
    try:
        appointment_data = request.json
        employee_id = appointment_data['employeeId']
        start_time = appointment_data['startTime']
        end_time = appointment_data['endTime']

        # Convert start_time and end_time strings to datetime objects
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')

        # Call the request handler to insert the appointment details
        handler.handle_save_work_schedule(employee_id, start_datetime, end_datetime)

        return jsonify({'success': True}), 200
    except Exception as e:
        print("main.py: save_work_schedule: ", e)
        return jsonify({'error': str(e)}), 500
    
@app.route('/get-work-schedule')
def get_work_schedule():
    # Fetch appointments with employee names from the database
    appointments = handler.handle_get_work_schedule()
    return jsonify(appointments)

@app.route('/submit-appointment', methods=['POST'])
def submit_appointment():
    print("submit-appointment")
    try:
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # Extract data from the request
        data = request.json
        date = data['date']
        time = data['time']
        employee_id = int(data['employee_id'])
        print(f'date:{date}, time:{time}, employee_id:{employee_id}')
        handler.handle_submit_appointment(employee_id, date, time, account_id)
        # Return a success message
        return jsonify({'message': 'Appointment submitted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/my-appointments', methods=['GET'])
def my_appointments():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    appointments= handler.handle_get_appointment_by_id(account_id)
    print(f'my_appointments:{appointments}')
    today = datetime.today().date()
    print(today)
    return render_template('my-appointments.html',appointments=appointments,today=today)

@app.route('/employee-appointments', methods=['GET'])
def employee_appointments():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    appointments= handler.handle_get_appointment_by_employee_id(account_id)
    print(f'employee_appointments:{appointments}')
    today = datetime.today().date()
    print(today)
    return render_template('employee-appointments.html',appointments=appointments,today=today)

@app.route('/all-appointments', methods=['GET'])
def all_appointments():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    appointments= handler.handle_get_all_appointment()
    print(f'all_appointments:{appointments}')
    today = datetime.today().date()
    print(today)
    return render_template('all-appointments.html',appointments=appointments,today=today)

@app.route('/cancel-appointment', methods=['POST'])
def cancel_appointment():
    try:
        appointment_id=request.json.get('appointment_id')
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # Delete the appointment from the database and return to the available appointments
        handler.handle_cancel_appointment(appointment_id)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to delete this apprenticeship.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/approve-appointment', methods=['POST'])
def approve_appointment():
    try:
        appointment_id=request.json.get('appointment_id')
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # approve the appointment
        handler.handle_approve_appointment(appointment_id)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to delete this apprenticeship.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
       
@app.route('/dashboard', methods=['GET'])
def dashboard():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    return render_template('dashboard.html')

@app.route('/apprenticeship', methods=['GET'])
def apprenticeship():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)

    # Fetch apprenticeship from the database
    apprenticeships = handler.handle_list_apprenticeship(account_id)
    return render_template('apprenticeship.html',apprenticeships=apprenticeships,account_id=account_id)

@app.route('/old-apprenticeship', methods=['GET'])
def oldApprenticeship():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)

    # Fetch apprenticeship from the database
    apprenticeships = handler.handle_list_old_apprenticeship()
    return render_template('old-apprenticeship.html',apprenticeships=apprenticeships,account_id=account_id)

@app.route('/my-apprenticeship', methods=['GET'])
def myApprenticeship():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)

    # Fetch apprenticeship from the database
    apprenticeships = handler.handle_list_apprenticeship_by_account_id(account_id)
    today = datetime.today().date()
    print(today)
    return render_template('my-apprenticeship.html',apprenticeships=apprenticeships,account_id=account_id, today=today)



@app.route('/create-apprenticeship', methods=['GET'])
def createApprenticeship():
     return render_template('create-apprenticeship.html')

@app.route('/create-apprenticeship', methods=['POST'])
def create_apprenticeship():
    
    try:
        handler.handle_create_apprenticeship(request.json)
        
        # Redirect or return a success message as needed
        print(f'The submitted data is: {request.json}')
        return redirect(url_for('apprenticeship'))
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
        return "An error occurred while creating the apprenticeship", 500
    
@app.route('/delete-apprenticeship', methods=['POST'])
def delete_apprenticeship():
    try:
        apprenticeship_id=request.json.get('apprenticeship_id')
        print('apprenticeship_id: ',apprenticeship_id)
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        # Delete the apprenticeship from the database
        handler.handle_delete_apprenticeship(apprenticeship_id)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to delete this apprenticeship.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/edit-apprenticeship/<int:apprenticeship_id>', methods=['GET'])
def editApprenticeship(apprenticeship_id):
     apprenticeship = handler.handle_get_apprenticeship_by_id(apprenticeship_id)
     return render_template('edit-apprenticeship.html',apprenticeship=apprenticeship)

@app.route('/edit-apprenticeship/<int:apprenticeship_id>', methods=['POST'])
def edit_apprenticeship(apprenticeship_id):
    try:
        # Extract JSON data from the request
        data = request.json
        
        # Call the handler function to handle the edit
        handler.handle_edit_apprenticeship(data, apprenticeship_id)
        
        # Redirect to the apprenticeship page after successful edit
        return redirect(url_for('apprenticeship'))
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Handle errors and return an appropriate response
        return "An error occurred while editing the apprenticeship", 500
    
@app.route('/registered-users/<int:apprenticeship_id>')
def get_registered_users(apprenticeship_id):
    # Fetch the names of registered users for the selected apprenticeship from the database
    registered_users = handler.handle_registered_users(apprenticeship_id)
    return jsonify(registered_users)

@app.route('/waiting-users/<int:apprenticeship_id>')
def get_waiting_users(apprenticeship_id):
    # Fetch the names of waiting users for the selected apprenticeship from the database
    registered_users = handler.handle_waiting_users(apprenticeship_id)
    return jsonify(registered_users)
    
@app.route('/apprenticeship-registration', methods=['POST'])
def apprenticeship_registration():
    try:
        apprenticeship_id=request.json.get('apprenticeship_id')
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        handler.handle_apprenticeship_registration(apprenticeship_id,cookie)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to register to this apprenticeship.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/apprenticeship-waiting-list', methods=['POST'])
def apprenticeship_waiting_list():
    try:
        apprenticeship_id=request.json.get('apprenticeship_id')
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        handler.handle_apprenticeship_waiting_list(apprenticeship_id,cookie)
        return jsonify({'success': True}), 200
    except KeyError as e:
        print(f'Cookie {COOKIE_NAME} not found in request')
        return jsonify({'error': 'You are not authorized to register to this apprenticeship waiting list.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/delete-registration', methods=['POST'])
def delete_registration():
    try:
        # Extract the apprenticeship ID and user ID from the request JSON
        apprenticeship_id = request.json.get('apprenticeship_id')
        account_id = request.json.get('account_id')

        # Call the handler function to delete the registration
        success = handler.handle_delete_registration(apprenticeship_id, account_id)

        if success:
            # Check if there are users in the waiting list for the same apprenticeship
            waiting_list_user = handler.handle_get_waiting_list_users(apprenticeship_id)

            if waiting_list_user:
                    # Update the user's status to "registered"
                    handler.handle_update_waiting_list_user_status(waiting_list_user, apprenticeship_id, "registered")

                    # Add a notification to the user's notifications table
                    notification_message = "איזה כיף! יצאת מרשימת המתנה של התלמדות, כנסי למסך ההתלמדויות כדי לראות את הרשמתך"
                    handler.handle_add_notification(waiting_list_user, notification_message)

            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to delete registration'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/review/<int:apprenticeship_id>', methods=['GET'])
def review(apprenticeship_id):
    apprenticeship = handler.handle_get_apprenticeship_by_id(apprenticeship_id)
    return render_template('review.html', apprenticeship=apprenticeship)

@app.route('/submit-review/<int:apprenticeship_id>', methods=['POST'])
def submit_review(apprenticeship_id):
    try:
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
        print('submit-review: apprenticeship_id: ', request.json)
        success = handler.handle_submit_review(request.json, apprenticeship_id, account_id)
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to submit review'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apprenticeship-review/<int:apprenticeship_id>', methods=['GET'])
def getReviews(apprenticeship_id):
    reviews = handler.handle_get_apprenticeship_review(apprenticeship_id)
    return render_template('apprenticeship-review.html', reviews=reviews)

# Route to handle the notifications page
@app.route('/notifications', methods=['GET'])
def notifications():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)
    notifications = handler.handle_get_notifications(account_id)
    print(f'notifications: {notifications}')
    return render_template('notifications.html', notifications=notifications,account_id=account_id)


if __name__ == '__main__':
    # Run the Flask application in debug mode on localhost (port 5000)
    app.run(host='0.0.0.0', port=3000, debug=True)
