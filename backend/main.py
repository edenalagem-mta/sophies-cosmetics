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
    if request.form.get('account_type') == 'לקוחה':
        # Redirect the customer to a different page
        return render_template('make-appointment.html')
    
    # Redirect other account types to a generic welcome page
    #TODO: redirect each costumer, manager, employer to a different page
    return redirect('/dashboard')

@app.route('/make-appointment', methods=['GET'])
def make_appointment():
     # TODO: FE should not display days that have passed. Should be greyed out or something

     # build dict of [date]->([time]->employees)
     appointments_by_date = handler.handle_list_available_appointments()
     print('make_appointment: appointments_by_date: ', appointments_by_date)
     appointments_by_date_json = json.dumps({
         k.strftime('%d-%m-%Y'):v for k,v in appointments_by_date.items()
     })
     return render_template('make-appointment.html', appointments_by_date=appointments_by_date_json)

# @app.route('/Work-constraints', methods=['GET'])
# def Work_constraints():
#      return render_template('Work-constraints.html')

@app.route('/navbar', methods=['GET'])
def show_navbar():
    try:
        cookie = request.cookies.get(COOKIE_NAME)
        user_first_name, user_last_name, user_account_type, account_id = handler.handle_get_first_and_last_name(cookie)
        print(f'The user details: {user_first_name} {user_last_name}, The account id:{account_id}')
        return render_template('navbar.html', user_first_name=user_first_name, user_last_name=user_last_name,user_account_type=user_account_type)
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
       
@app.route('/dashboard', methods=['GET'])
def dashboard():
     return render_template('dashboard.html')

@app.route('/apprenticeship', methods=['GET'])
def apprenticeship():
    cookie = request.cookies.get(COOKIE_NAME)
    user_first_name, user_last_name, user_email, account_id = handler.handle_get_first_and_last_name(cookie)

    # Fetch apprenticeship from the database
    apprenticeships = handler.handle_list_apprenticeship(account_id)
    return render_template('apprenticeship.html',apprenticeships=apprenticeships,account_id=account_id)


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

        print(f'delete-registration:' , apprenticeship_id, account_id)

        # Call the handler function to delete the registration
        success = handler.handle_delete_registration(apprenticeship_id, account_id)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to delete registration'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    



if __name__ == '__main__':
    # Run the Flask application in debug mode on localhost (port 5000)
    app.run(host='0.0.0.0', port=8080, debug=True)
