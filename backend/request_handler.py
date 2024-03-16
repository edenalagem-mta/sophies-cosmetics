import urllib.parse
import json
import mysql.connector
import hashlib
import os
from datetime import datetime, timedelta
import http.client


def invert_dict(d):
        return dict(map(reversed, d.items()))


class RequestHandler(object):
    def __init__(self) -> None:
        #Create connection to sql
        self.mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="sophiecosmetics"
        )
        self.mycursor = self.mydb.cursor()
        self.signed_in_users = dict()

        # Check if the connection was successful
        if self.mydb.is_connected():
            print("Connected to MySQL database")
    
    def hash_password(password):
        md5_hash = hashlib.md5(password.encode('utf-8'))
        return md5_hash.hexdigest()
    
    def handle_logout(self, cookie):
        self.signed_in_users.pop(cookie)

    def handle_signup(self, post_data):
        print(f'handle_signup: {post_data}')
        # Extract parameters from the form data
        account_type = post_data['account_type']
        first_name = post_data['first_name']
        last_name = post_data['last_name']
        email = post_data['email']
        birth_date = datetime.strptime(post_data['birth_date'], '%Y-%m-%d').date()
        password = post_data['password']
        address = post_data['address']
        phone = post_data['phone']
        
          # Check if email already exists in the database
        sql = "SELECT * FROM Accounts WHERE email = %s"
        val = (email,)
        self.mycursor.execute(sql, val)
        existing_user = self.mycursor.fetchone()

        if existing_user:
        # Send error response if email already exists
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = {'error': 'Email address already in use'}
            
            return response_data
        # Insert new user into the database
        sql = "INSERT INTO Accounts (email, password, first_name, last_name, address, account_type,birth_date, phone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        val = (email, password, first_name, last_name, address, account_type,birth_date, phone)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        return {'success': 'SignUp successful'}
    
    def handle_signup_cookie(self, post_data):
        # Extract email and password from the form data
        print(f'handle signup_cookie:{post_data}')
        email = post_data['email']
        password = post_data['password']

        # Connect to the database and check if the email and password match
        sql = "SELECT * FROM Accounts WHERE email = %s AND password = %s"
        val = (email, password)
        self.mycursor.execute(sql, val)
        account = self.mycursor.fetchone()
        if account:
            # Account exists, return True to indicate successful login
            account_id = account[0]
            if account_id in self.signed_in_users.values():
                # Get existing cookie for user
                return True, invert_dict(self.signed_in_users)[account_id]
            
            # Generate a unique cookie for this new sign-in session.
            cookie = os.urandom(32).hex()
            self.signed_in_users[cookie] = account_id
            
            print(f'handle_signup_cookie: self.signed_in_users = {self.signed_in_users}')
            return True, cookie
        # Account does not exist or credentials are incorrect
        return False, ''
        
    def handle_login(self, post_data):
       # Extract email and password from the form data
        print(f'handle login:{post_data}')
        email = post_data.get('email')
        password = post_data.get('password')

        # Connect to the database and check if the email and password match
        sql = "SELECT * FROM Accounts WHERE email = %s AND password = %s"
        val = (email, password)
        self.mycursor.execute(sql, val)
        account = self.mycursor.fetchone()
        if account:
            # Account exists, return True to indicate successful login
            account_id = account[0]
            if account_id in self.signed_in_users.values():
                # Get existing cookie for user
                return True, invert_dict(self.signed_in_users)[account_id]
            
            # Generate a unique cookie for this new sign-in session.
            cookie = os.urandom(32).hex()
            self.signed_in_users[cookie] = account_id
            
            print(f'handle_login: self.signed_in_users = {self.signed_in_users}')
            return True, cookie
        # Account does not exist or credentials are incorrect
        return False, ''
        #hashed_password = self.hash_password(password)

    def handle_get_first_and_last_name(self, cookie):
        # Extract email and password from the form data
        account_id = self.signed_in_users[cookie]
        print(f'handle_get_first_and_last_name: account_id = {account_id}')

        # Connect to the database and check if the email and password match
        sql = "SELECT email, account_type, first_name, last_name FROM Accounts WHERE account_id = %s"
        val = (account_id,)
        self.mycursor.execute(sql, val)
        account = self.mycursor.fetchone()
        print(f'account:{account}')

        if account:
            email = account[0]
            account_type = account[1]
            first_name = account[2]
            last_name = account[3]
            print(f'user details:{first_name},{last_name}, account id:{account_id}')

            # Return the first name and last name
            return first_name, last_name, account_type, account_id
        else:
            # Account not found
            return None, None, None, None

    def handle_create_subject(self, post_data, cookie):
       # Extract the subject details from the form data
        title = post_data['title']
        content = post_data['content']
        
        # Extract the account ID of the logged-in user from the session
        account_id = self.signed_in_users[cookie]
        print(f'handle_create_subject: account_id = {account_id}')
        
        # Insert the new subject into the database, including the account ID
        sql = "INSERT INTO subjects (title, content, account_id) VALUES (%s, %s, %s)"
        val = (title, content, account_id)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
            
        print(f'handle_create_subject: {post_data}')

    def handle_list_subjects(self):
        # Execute a SELECT query to fetch data from the table
        self.mycursor.execute("SELECT subjects.subject_id, subjects.title, subjects.content, subjects.account_id,CONCAT(accounts.first_name, ' ', accounts.last_name) AS account_name, COUNT(comments.subject_id) AS comment_count FROM subjects LEFT JOIN comments ON subjects.subject_id = comments.subject_id LEFT JOIN accounts ON subjects.account_id = accounts.account_id WHERE subjects.status = 'approved' GROUP BY subjects.subject_id ORDER BY subjects.date_and_time DESC")
        # Fetch all subjects from the result set
        list_subjects = self.mycursor.fetchall()
        subjects = [{'subject_id': row[0], 'title': row[1], 'content': row[2], 'account_id': row[3], 'account_name':row[4], 'comment_count': row[5]} for row in list_subjects]
        # print("Fetched subjects:", subjects)  # Print fetched subjects
        return subjects
    
    def handle_list_manager_subjects(self):
        # Execute a SELECT query to fetch data from the table
        self.mycursor.execute("SELECT subjects.subject_id, subjects.title, subjects.content, subjects.account_id,CONCAT(accounts.first_name, ' ', accounts.last_name) AS account_name, COUNT(comments.subject_id) AS comment_count FROM subjects LEFT JOIN comments ON subjects.subject_id = comments.subject_id LEFT JOIN accounts ON subjects.account_id = accounts.account_id WHERE subjects.status = 'waitingForApprove' GROUP BY subjects.subject_id ORDER BY subjects.date_and_time DESC")
        # Fetch all subjects from the result set
        list_subjects = self.mycursor.fetchall()
        subjects = [{'subject_id': row[0], 'title': row[1], 'content': row[2], 'account_id': row[3],'account_name':row[4], 'comment_count': row[5]} for row in list_subjects]
        print("Fetched subjects:", subjects)  # Print fetched subjects
        return subjects
    
    def handle_list_comments(self, subject_id):
        # Execute a SELECT query to fetch comments related to the subject_id
        self.mycursor.execute("SELECT subject_id, content FROM comments WHERE subject_id = %s", (subject_id,))
        
        # Fetch all comments related to the subject_id from the result set
        list_comments = self.mycursor.fetchall()
        
        # Convert fetched comments to a list of dictionaries
        comments = [{'subject_id': row[0], 'content': row[1]} for row in list_comments]
        
        # Print fetched comments for debugging
        print("Fetched comments:", comments)
        
        return comments
    
    def approve_subject(self, subject_id):
        try:
            # Execute a update query to update the subject
            sql = "UPDATE subjects SET status = 'approved' WHERE subject_id = %s"
            val = (subject_id,)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            print(f"Subject with ID {subject_id} approved successfully")
            return True
        except Exception as e:
            print(f"Error approving subject: {str(e)}")
            return False
    
    def delete_subject(self, subject_id):
        try:
            # Delete comments associated with the subject
            sql_delete_comments = "DELETE FROM comments WHERE subject_id = %s"
            self.mycursor.execute(sql_delete_comments, (subject_id,))
            self.mydb.commit()
            # Execute a DELETE query to remove the subject from the database
            sql = "DELETE FROM subjects WHERE subject_id = %s"
            val = (subject_id,)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            print(f"Subject with ID {subject_id} deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting subject: {str(e)}")
            return False
    

    def handle_submit_comment(self, post_data):
        subject_id = post_data['subject_id']
        content = post_data['content']
        
        # Insert the comment into the database
        sql = "INSERT INTO comments (subject_id, content) VALUES (%s, %s)"
        val = (subject_id, content)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        print(f'handle_submit_comment: {post_data}')

    
    def handle_add_work_constraints(self, post_data, cookie):
        # Extract data from the form
        date = post_data['dates']
        times = post_data.getlist('times[]')  # Retrieve all selected time slots as a list
        account_id = self.signed_in_users.get(cookie)
        # Insert each time slot into the database
        for time in times:
            sql = "INSERT INTO WorkConstraints (account_id, constraint_date, constraint_time) VALUES (%s, %s, %s)"
            val = (account_id, date, time)
            self.mycursor.execute(sql, val)
        self.mydb.commit()
        print(f'handle_add_work_constraints: {post_data}')

    def handle_get_work_constraints(self, cookie):
        account_id = self.signed_in_users.get(cookie)
        print(f'handle_get_work_constraints: account_id:',account_id)
        sql = "SELECT * FROM WorkConstraints WHERE account_id = %s"
        val = (account_id,)
        self.mycursor.execute(sql, val)
        constraints = self.mycursor.fetchall()
        print(f'handle_get_work_constraints: constraints: ',constraints)
        return constraints
    
    def handle_get_work_constraints_for_all_employees(self):
        try:
            # Fetch work constraints for all employees along with their account details
            sql = """
            SELECT wc.id, wc.constraint_date, wc.constraint_time, a.first_name, a.last_name
            FROM WorkConstraints wc
            JOIN Accounts a ON wc.account_id = a.account_id
            """
            self.mycursor.execute(sql)
            constraints = self.mycursor.fetchall()
            return constraints
        except Exception as e:
            # Handle errors and return an appropriate response
            print(f"An error occurred: {str(e)}")
            return []
    
    def handle_delete_work_constraint(self, constraint_id):
        sql = "DELETE FROM WorkConstraints WHERE id = %s"
        val = (constraint_id,)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        
    def handle_get_employees(self):
        try:
            # Execute SQL query to select employees based on account_type
            sql = "SELECT * FROM Accounts WHERE account_type = %s"
            val = ("עובדת",)
            self.mycursor.execute(sql, val)
            employees = self.mycursor.fetchall()
            print(f'handle_get_employees:',employees)
            return employees
        except Exception as e:
            # Handle errors and return an appropriate response
            print(f"An error occurred: {str(e)}")
            return []
        
    def handle_save_work_schedule(self, employee_id, start_datetime, end_datetime):
        try:
            # TODO: Break schedule into 1-hour pieces,
            #       check if any of the pieces exists in the employee constraints table.
            #       If found any of them in the table, return an error.

            # TODO: prevent half-hours (maybe even in UI?)

            # Iterate over hours between start_time and end_time
            current_datetime = start_datetime
            while current_datetime < end_datetime:
                # Insert each hour as a separate row in the SQL table
                sql = "INSERT INTO available_appointments (account_id, date, start_time, end_time) VALUES (%s, %s, %s, %s)"
                end_of_current_interval = current_datetime + timedelta(hours=1)
                val = (employee_id, current_datetime.date(), current_datetime.time(), end_of_current_interval.time())
                print('handle_save_work_schedule: val = ', val)
                self.mycursor.execute(sql, val)

                # Increment current_datetime by 1 hour
                current_datetime = end_of_current_interval

            # Commit the transaction
            self.mydb.commit()

            print("Appointment details saved successfully")
        except Exception as e:
            print(f"Error saving appointment details: {str(e)}")
            # Rollback the transaction if an error occurs
            self.mydb.rollback()
    
    @staticmethod
    def fix_appointment_datetimes(appointment: tuple):
        result = appointment[:2]
        result += (
            {
                'hour': int(appointment[2].seconds / 3600),
                'minute': int((appointment[2].seconds % 3600) / 60)
            },
            {
                'hour': int(appointment[3].seconds / 3600),
                'minute': int((appointment[3].seconds % 3600) / 60)
            }
        )
        return result + appointment[4:]

    def handle_get_work_schedule(self):
        return self.list_work_schedule(datetime.today(), datetime.today() + timedelta(days=31), include_booked=True)

    def list_work_schedule(self, start_date, end_date, include_booked=False):
        # TODO: sql should filter for start and end dates
        current_datetime = datetime.now()

        where = 'WHERE (a.date BETWEEN %s AND %s) AND (a.date > %s OR (a.date = %s AND a.end_time > %s))'
        val = (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            current_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            current_datetime.strftime('%Y-%m-%d'),
            current_datetime.strftime('%H:%M:%S')
        )

        if not include_booked:
            where = f'{where} AND (availability_status = 1)'

        try:
            # Execute SQL query to fetch appointments with employee names
            sql = f"""
                SELECT a.available_appointment_id, a.date, a.start_time, a.end_time, a.account_id, e.first_name, e.last_name
                FROM available_appointments a
                INNER JOIN accounts e ON a.account_id = e.account_id
                {where}
            """
            self.mycursor.execute(sql, val)
            appointments = self.mycursor.fetchall()
            appointments = list(map(RequestHandler.fix_appointment_datetimes, appointments))
            print(f'handle_get_work_schedule: appointments:', appointments)
            return appointments
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return []
    
    def handle_list_available_appointments(self):
        # 31 days ahead, build map of date -> (time -> employees)
        days_ahead_for_schedule = 31
                       
        current_date = datetime.today()
        
        schedule = self.list_work_schedule(current_date, current_date+timedelta(days=days_ahead_for_schedule-1))

        result = dict()
        for i in range(days_ahead_for_schedule):
            iteration_date = (current_date + timedelta(days=i)).date()

            day_availability = dict()
            
            # filter out all rows that don't have our iteration date
            relevant_rows = filter(lambda row: row[1] == iteration_date, schedule)

            # for each of the rows with our date, extract employee id and place it in the correct hour key
            for row in relevant_rows:
                hour = row[2]['hour']

                if hour not in day_availability:
                    day_availability[hour] = []
                
                # row[4] is employee id, row[5] is first name, row[6] is last name
                day_availability[hour].append({
                    'id': row[4],
                    'name': f'{row[5]} {row[6]}'
                })

            result[iteration_date] = day_availability
        
        return result
    
    def handle_get_phone_by_account_id(self, account_id):
        try:
            sql = """SELECT phone
                FROM accounts
                WHERE account_id = %s"""
            val = (account_id,)
            self.mycursor.execute(sql, val)
            phone = self.mycursor.fetchall()
            print(f'handle_get_phone_by_account_id:{phone}')
            return phone
        except Exception as e:
            print(f"Error getting phone by account_id: {str(e)}")
            return None


    
    def handle_submit_appointment(self, employee_id, date, time, account_id):
        try:
            # Parse the string date into a datetime object
            date_obj = datetime.strptime(date, '%d-%m-%Y').date()
            print(f'handle_submit_appointment date:{date_obj}')
            sql="INSERT INTO appointments (employee_id, date, time, account_id) VALUES (%s, %s, %s, %s)"
            val = (employee_id, date_obj, time, account_id)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            # Update availability_status in available_appointments table
            sql_update = "UPDATE available_appointments SET availability_status = 0 WHERE account_id = %s AND date = %s AND start_time = %s"
            val_update = (employee_id, date_obj, time)
            self.mycursor.execute(sql_update, val_update)
            self.mydb.commit()
            phone = self.handle_get_phone_by_account_id(account_id)
            conn = http.client.HTTPSConnection("graph.facebook.com")
            payload = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"{phone}",
            "type": "text",
            "text": {
                "preview_url": False,
                "body": f"איזה כיף! נקבע לך תור לציפורניים אצל sophie's cosmetics ב {date_obj} בשעה {time}. מחכות לראות אותך!"
            }
            })
            headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer EAANVkcpkjS8BOxawpPNpXrjlEsaZB9gOW84Jj03qWTHP7qE2TjX9IA3xIUOtgCADOPCKLmwc4GlcAZA91O2lUoUFf1t08dycxPSlliNmYtFsbStmHsZCajXHeYONNxDplebZCArmZAaabpGvNcYx1B8ErpHLJ1L6MQ7ZBMJ5oj3NOrYkDX6cGwt1u921v1JxZBK'
            }
            conn.request("POST", "/v18.0/255881987605669/messages", payload, headers) 
            res = conn.getresponse() 
            data = res.read()
            print(data.decode("utf-8"))
            return True
        except Exception as e:
            print(f"Error submit appointment: {str(e)}")
            return False
        
    def handle_get_appointment_by_id(self, account_id):
        try:
            # Execute SQL query to retrieve appointments by account ID
            sql = """
                SELECT a.*, CONCAT(e.first_name, ' ', e.last_name) AS employee_name
                FROM appointments a
                INNER JOIN accounts e ON a.employee_id = e.account_id
                WHERE a.account_id = %s
                """
            val = (account_id,)
            self.mycursor.execute(sql, val)
            appointments = self.mycursor.fetchall()

            # Return the list of appointments
            return appointments
        except Exception as e:
            print(f"Error fetching appointments: {str(e)}")
            return None
        
    def handle_get_appointment_by_employee_id(self, account_id):
        try:
            # Execute SQL query to retrieve appointments by employee ID
            sql = """
                SELECT a.*, CONCAT(e.first_name, ' ', e.last_name) AS costumer_name
                FROM appointments a
                INNER JOIN accounts e ON a.account_id = e.account_id
                WHERE a.employee_id = %s
                """
            val = (account_id,)
            self.mycursor.execute(sql, val)
            appointments = self.mycursor.fetchall()

            # Return the list of appointments
            return appointments
        except Exception as e:
            print(f"Error fetching appointments: {str(e)}")
            return None
    
    def handle_get_all_appointment(self):
        try:
            # Execute SQL query to retrieve appointments
            sql = """
                SELECT 
                    a.appointment_id, 
                    a.date, 
                    a.time, 
                    CONCAT(employee.first_name, ' ', employee.last_name) AS employee_name,
                    CONCAT(account.first_name, ' ', account.last_name) AS account_name,
                    a.status
                FROM 
                    appointments a
                INNER JOIN 
                    accounts employee ON a.employee_id = employee.account_id
                INNER JOIN
                    accounts account ON a.account_id = account.account_id;
                """
            self.mycursor.execute(sql)
            appointments = self.mycursor.fetchall()

            # Return the list of appointments
            return appointments
        except Exception as e:
            print(f"Error fetching appointments: {str(e)}")
            return None

    def handle_cancel_appointment(self, appointment_id):
        try:
            # Retrieve appointment details from the appointments table
            sql_select = "SELECT * FROM appointments WHERE appointment_id = %s"
            val_select = (appointment_id,)
            self.mycursor.execute(sql_select, val_select)
            appointment = self.mycursor.fetchone()

            if appointment:
                start_time = appointment[2]  # Index 2 corresponds to the time column
                end_time = start_time + timedelta(hours=1)  # End time is 1 hour after start time
                print(f'handle_cancel_appointment- start_time:{start_time}, end_time:{end_time}, date{appointment[1]}, account_id:{appointment[5]}')
                # Move the appointment back to the available_appointments table
                sql_update = "UPDATE available_appointments SET availability_status = 1 WHERE account_id = %s AND date = %s AND start_time = %s And end_time = %s"
                val_update = (appointment[5], appointment[1], start_time, end_time)
                self.mycursor.execute(sql_update, val_update)

                # Delete the appointment from the appointments table
                sql_delete = "DELETE FROM appointments WHERE appointment_id = %s"
                val_delete = (appointment_id,)
                self.mycursor.execute(sql_delete, val_delete)

                self.mydb.commit()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error canceling appointment: {str(e)}")
            return False
    
    def handle_approve_appointment(self, appointment_id):
        try:
            sql = "UPDATE appointments SET status = 'approved' WHERE appointment_id = %s"
            val = (appointment_id,)
            self.mycursor.execute(sql,val)
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Error approving appointment: {str(e)}")
            return False


    
    def build_apprenticeship_dict(self, row):
        return {
            'apprenticeship_id': row[0],
            'title': row[1],
            'description': row[2],
            'startDate': row[3],
            'endDate': row[4],
            'day_of_week': row[5],
            'time': row[6],
            'price': row[7],
            'duration': row[8],
            'num_registrations': row[9],
            'amount_of_people': row[10],
            'status': row[11]
        }
    
    def handle_list_apprenticeship(self, user_account_id):
        # Execute a SELECT query to fetch data from the table
        self.mycursor.execute("SELECT apprenticeships.apprenticeship_id, apprenticeships.title, apprenticeships.description, apprenticeships.startDate, apprenticeships.endDate, apprenticeships.day_of_week, apprenticeships.time, apprenticeships.price, apprenticeships.duration, apprenticeships.num_registrations, apprenticeships.amount_of_people, COALESCE(apprenticeship_registration.status, 'Not Registered') AS status FROM apprenticeships LEFT JOIN apprenticeship_registration ON apprenticeships.apprenticeship_id = apprenticeship_registration.apprenticeship_id AND apprenticeship_registration.account_id = %s WHERE apprenticeships.startDate >= CURDATE() ORDER BY apprenticeships.startDate DESC", (user_account_id,))
        list_apprenticeships = self.mycursor.fetchall()

        # Convert date strings to formatted strings
        apprenticeships = [self.build_apprenticeship_dict(row) for row in list_apprenticeships]
        print(f'handle_list_apprenticeship:', apprenticeships)
        return apprenticeships

    def build_old_apprenticeship_dict(self, row):
        return {
            'apprenticeship_id': row[0],
            'title': row[1],
            'description': row[2],
            'startDate': row[3],
            'endDate': row[4],
            'day_of_week': row[5],
            'time': row[6],
            'price': row[7],
            'duration': row[8],
            'num_registrations': row[9],
            'amount_of_people': row[10]
        }
    
    def handle_list_old_apprenticeship(self):
        # Execute a SELECT query to fetch data from the table
        self.mycursor.execute("SELECT apprenticeships.apprenticeship_id, apprenticeships.title, apprenticeships.description, apprenticeships.startDate, apprenticeships.endDate, apprenticeships.day_of_week, apprenticeships.time, apprenticeships.price, apprenticeships.duration, apprenticeships.num_registrations,apprenticeships.amount_of_people  FROM apprenticeships WHERE apprenticeships.startDate < CURDATE() ORDER BY apprenticeships.startDate DESC")
        list_apprenticeships = self.mycursor.fetchall()

        # Convert date strings to formatted strings
        return [self.build_old_apprenticeship_dict(row) for row in list_apprenticeships]
    
    def handle_list_apprenticeship_by_account_id(self, account_id):
        try:
            # Execute a SELECT query to fetch data from the table
            sql = """SELECT a.apprenticeship_id, a.title, a.description, a.startDate, a.endDate, 
                            a.day_of_week, a.time, a.price, a.duration, a.num_registrations, a.amount_of_people  
                    FROM apprenticeships a
                    INNER JOIN apprenticeship_registration ar ON a.apprenticeship_id = ar.apprenticeship_id
                    WHERE ar.account_id = %s AND ar.status = 'registered' 
                    ORDER BY a.startDate DESC"""
            
            # Execute the query with account_id as parameter
            self.mycursor.execute(sql, (account_id,))
            
            # Fetch all the rows from the result set
            list_apprenticeships = self.mycursor.fetchall()
            print(f'handle list apprenticeship by account id:{list_apprenticeships}')
            # Convert date strings to formatted strings
            return [self.build_old_apprenticeship_dict(row) for row in list_apprenticeships]
        except Exception as e:
            print(f"An error occurred while fetching apprenticeships by account ID: {str(e)}")
            return None

    def handle_get_apprenticeship_by_id(self,apprenticeship_id):
        # Execute a SELECT query to fetch the apprenticeship details by ID
        self.mycursor.execute("SELECT apprenticeship_id, title, description, startDate, endDate, day_of_week, time, price, duration, num_registrations, amount_of_people, amount_of_meetings FROM apprenticeships WHERE apprenticeship_id = %s", (apprenticeship_id,))
        apprenticeship_data = self.mycursor.fetchone()

        # Check if the apprenticeship data exists
        if apprenticeship_data:
            # Construct a dictionary containing the apprenticeship details
            apprenticeship = {
                'apprenticeship_id': apprenticeship_data[0],
                'title': apprenticeship_data[1],
                'description': apprenticeship_data[2],
                'startDate': apprenticeship_data[3],
                'endDate': apprenticeship_data[4],
                'day_of_week': apprenticeship_data[5],
                'time': apprenticeship_data[6],
                'price': apprenticeship_data[7],
                'duration': apprenticeship_data[8],
                'num_registrations': apprenticeship_data[9],
                'amount_of_people': apprenticeship_data[10],
                'amount_of_meetings':apprenticeship_data[11]
            }
            return apprenticeship
        else:
            # If no apprenticeship found with the provided ID, return None 
            return None
        
    def handle_edit_apprenticeship(self, post_data, apprenticeship_id):
        # Extract the apprenticeship details from the form data
        title = post_data['title']
        description = post_data['description']
        startDate = post_data['startDate']
        endDate=post_data['endDate']
        hour=post_data['hour']
        days=post_data['days']
        duration=post_data['duration']
        amount_of_meetings=post_data['amount_of_meetings']
        amount_of_people=post_data['amount_of_people']
        price=post_data['price']
        # image=post_data['image']
        # update the apprenticeship into the database
        #TODO: add insert image
        sql = "UPDATE apprenticeships SET title = %s, description = %s, startDate = %s, endDate = %s, day_of_week = %s, time = %s, price = %s, duration = %s, amount_of_people = %s, amount_of_meetings = %s WHERE apprenticeship_id = %s"
        self.mycursor.execute(sql, (title, description, startDate, endDate, days, hour, price, duration, amount_of_people, amount_of_meetings, apprenticeship_id))
        self.mydb.commit()

    def handle_registered_users(self, apprenticeship_id):
        try:
            # Fetch the first and last names of registered users for the selected apprenticeship
            sql = "SELECT a.first_name, a.last_name FROM apprenticeship_registration ar JOIN accounts a ON ar.account_id = a.account_id WHERE ar.apprenticeship_id = %s AND ar.status = 'registered'"
            self.mycursor.execute(sql, (apprenticeship_id,))
            registered_users = self.mycursor.fetchall()
            # Convert the result into a list of dictionaries for JSON serialization
            result = [{'first_name': user[0], 'last_name': user[1]} for user in registered_users]
            return result
        except Exception as e:
            print(f"An error occurred while fetching registered users: {str(e)}")
            return None
        
    def handle_waiting_users(self, apprenticeship_id):
        try:
            # Fetch the first and last names of registered users for the selected apprenticeship
            sql = "SELECT a.first_name, a.last_name FROM apprenticeship_registration ar JOIN accounts a ON ar.account_id = a.account_id WHERE ar.apprenticeship_id = %s AND ar.status = 'waitingList'"
            self.mycursor.execute(sql, (apprenticeship_id,))
            registered_users = self.mycursor.fetchall()
            # Convert the result into a list of dictionaries for JSON serialization
            result = [{'first_name': user[0], 'last_name': user[1]} for user in registered_users]
            return result
        except Exception as e:
            print(f"An error occurred while fetching waiting users: {str(e)}")
            return None
    
    def handle_create_apprenticeship(self, post_data):
       # Extract the apprenticeship details from the form data
        title = post_data['title']
        description = post_data['description']
        startDate = post_data['startDate']
        endDate=post_data['endDate']
        hour=post_data['hour']
        days=post_data['days']
        duration=post_data['duration']
        amount_of_meetings=post_data['amount_of_meetings']
        amount_of_people=post_data['amount_of_people']
        price=post_data['price']
        # image=post_data['image']
        
        # Insert the new apprenticeship into the database
        #TODO: add insert image
        sql = "INSERT INTO apprenticeships (title, description, startDate, endDate, time, day_of_week, duration, amount_of_meetings, amount_of_people, price) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (title, description, startDate, endDate, hour, days, duration, amount_of_meetings, amount_of_people, price)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
            
        print(f'handle_create_apprenticeship: {post_data}')

    def handle_delete_apprenticeship(self, apprenticeship_id):
        try:
            # TODO: Delete users signup associated with the apprenticeship
            sql_delete_registrations = "DELETE FROM apprenticeship_registration WHERE apprenticeship_id = %s"
            self.mycursor.execute(sql_delete_registrations, (apprenticeship_id,))
            self.mydb.commit()
            # Execute a DELETE query to remove the apprenticeship from the database
            sql = "DELETE FROM apprenticeships WHERE apprenticeship_id = %s"
            val = (apprenticeship_id,)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            print(f"apprenticeship with ID {apprenticeship_id} deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting apprenticeship: {str(e)}")
            return False
        
    def handle_apprenticeship_registration(self, apprenticeship_id,cookie):
        try:
            # Get the current date and time for registration_date
            registration_date = datetime.now()
            account_id = self.signed_in_users[cookie]
            status = "registered"
            # Perform the database operation to insert the registration
            sql = "INSERT INTO Apprenticeship_registration (apprenticeship_id, account_id, registration_date, status) VALUES (%s, %s, %s, %s)"
            val = (apprenticeship_id, account_id, registration_date, status)
            self.mycursor.execute(sql, val)
            self.mydb.commit()

             # Update the apprenticeship table to increment num_registrations
            sql_update_apprenticeship = "UPDATE apprenticeships SET num_registrations = num_registrations + 1 WHERE apprenticeship_id = %s"
            self.mycursor.execute(sql_update_apprenticeship, (apprenticeship_id,))
            self.mydb.commit()

            # Return a success message
            return "Registration successful"

        except Exception as e:
            print(f"An error occurred while registering: {str(e)}")
            return None
        
    def handle_apprenticeship_waiting_list(self, apprenticeship_id,cookie):
        try:
            # Get the current date and time for registration_date
            registration_date = datetime.now()
            account_id = self.signed_in_users[cookie]
            status = "waitingList"
            # Perform the database operation to insert the registration
            sql = "INSERT INTO Apprenticeship_registration (apprenticeship_id, account_id, registration_date, status) VALUES (%s, %s, %s, %s)"
            val = (apprenticeship_id, account_id, registration_date, status)
            self.mycursor.execute(sql, val)
            self.mydb.commit()

            # Return a success message
            return "Registration to waiting list successful"

        except Exception as e:
            print(f"An error occurred while registering: {str(e)}")
            return None
        
    def handle_delete_registration(self, apprenticeship_id, account_id):
        try:
            # Check if the user's registration status is "registered" before updating num_registrations
            self.mycursor.execute("SELECT status FROM apprenticeship_registration WHERE apprenticeship_id = %s AND account_id = %s", (apprenticeship_id, account_id))
            registration_status = self.mycursor.fetchone()
            
            if registration_status and registration_status[0] == "registered":
                # Decrement num_registrations only if the user's registration status is "registered"
                self.mycursor.execute("UPDATE apprenticeships SET num_registrations = num_registrations - 1 WHERE apprenticeship_id = %s", (apprenticeship_id,))
                
            # Delete the user's registration record regardless of the status
            self.mycursor.execute("DELETE FROM apprenticeship_registration WHERE apprenticeship_id = %s AND account_id = %s", (apprenticeship_id, account_id))
            
            # Commit the changes to the database
            self.mydb.commit()
            return True
        
        except Exception as e:
            print(f"An error occurred while cancel registration: {str(e)}")
            return False
        
    def handle_get_waiting_list_users(self,apprenticeship_id):
        try:
            # Execute a SELECT query to fetch users in the waiting list for the specified apprenticeship
            sql = "SELECT account_id FROM apprenticeship_registration WHERE apprenticeship_id = %s AND status = 'waitingList' ORDER BY registration_date LIMIT 1"
            self.mycursor.execute(sql, (apprenticeship_id,))
            waiting_list_user = self.mycursor.fetchone()
            print(f'handle_get_waiting_list_users:{waiting_list_user}, account_id:{waiting_list_user[0]}')

            # Return the waiting list user
            if waiting_list_user:
                return waiting_list_user[0]  # Return the account_id
            else:
                return None
        except Exception as e:
            print(f"An error occurred while fetching waiting list users: {str(e)}")
            return None
        
    def handle_update_waiting_list_user_status(self, account_id,apprenticeship_id, status):
        try:
            # Update the status of the user in the waiting list
            sql = "UPDATE apprenticeship_registration SET status = %s WHERE account_id = %s And apprenticeship_id = %s"
            self.mycursor.execute(sql, (status, account_id, apprenticeship_id))
            self.mycursor.execute("UPDATE apprenticeships SET num_registrations = num_registrations + 1 WHERE apprenticeship_id = %s", (apprenticeship_id,))

            # Commit the changes to the database
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"An error occurred while updating waiting list user status: {str(e)}")
            return False
        
    def handle_add_notification(self, account_id, notification_message):
        try:
            # Insert the notification into the notifications table
            sql = "INSERT INTO notifications (account_id, notification_message) VALUES (%s, %s)"
            self.mycursor.execute(sql, (account_id, notification_message))

            # Commit the changes to the database
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"An error occurred while adding notification: {str(e)}")
            return False
        
    def handle_submit_review(self, post_data, apprenticeship_id, account_id):
        try:
            # Extract the review details from the form data
            satisfaction_storeup = post_data['satisfactionStoreup']
            satisfaction_storeexp = post_data['satisfactionStoreexp']
            satisfaction_storeteq = post_data['satisfactionStoreteq']
            satisfaction_store = post_data['satisfactionStore']
            comments = post_data['comments']
            
            # Insert the review into the database
            sql = "INSERT INTO apprenticeship_reviews (apprenticeship_id, account_id, satisfaction_storeup, satisfaction_storeexp, satisfaction_storeteq, satisfaction_store, comments) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            val = (apprenticeship_id, account_id, satisfaction_storeup, satisfaction_storeexp, satisfaction_storeteq, satisfaction_store, comments)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            
            return True
        except Exception as e:
            print(f"An error occurred while submitting the review: {str(e)}")
            return False
        
    def handle_get_apprenticeship_review(self, apprenticeship_id):
        try:
            # Execute the SQL query to fetch data
            sql = """
                SELECT 
                    r.apprenticeship_id, 
                    r.account_id, 
                    a.title AS apprenticeship_title, 
                    CONCAT(ac.first_name, ' ', ac.last_name) AS account_name, 
                    r.satisfaction_storeup, 
                    r.satisfaction_storeexp, 
                    r.satisfaction_storeteq, 
                    r.satisfaction_store, 
                    r.comments 
                FROM 
                    apprenticeship_reviews r 
                JOIN 
                    accounts ac ON r.account_id = ac.account_id 
                JOIN 
                    apprenticeships a ON r.apprenticeship_id = a.apprenticeship_id 
                WHERE 
                    r.apprenticeship_id = %s
            """
            self.mycursor.execute(sql, (apprenticeship_id,))
            
            # Fetch all rows from the result set
            reviews_data = self.mycursor.fetchall()
            
            # Check if any rows were returned
            if reviews_data:
                # Construct a list of dictionaries containing review details
                reviews = [{
                    'apprenticeship_id': row[0],
                    'account_id': row[1],
                    'apprenticeship_title': row[2],
                    'account_name': row[3],
                    'satisfaction_storeup': row[4],
                    'satisfaction_storeexp': row[5],
                    'satisfaction_storeteq': row[6],
                    'satisfaction_store': row[7],
                    'comment': row[8],
                } for row in reviews_data]
                return reviews
            else:
                # No rows found for the given apprenticeship_id
                return None
        except Exception as e:
            # Log the error message for debugging
            print(f"An error occurred while fetching apprenticeship reviews by apprenticeship ID: {str(e)}")
            return None
        
    def handle_get_unread_notification_count(self, account_id):
        try:
            sql = "SELECT COUNT(*) FROM notifications WHERE account_id = %s AND status = 0"
            self.mycursor.execute(sql, (account_id,))
            unread_notification_count = self.mycursor.fetchone()[0]  # Fetch the count of unread notifications           
            return unread_notification_count
        except Exception as e:
            print(f"An error occurred while getting unread notification count: {str(e)}")
            return 0  # Return 0 in case of any error or no notifications found
        
    def handle_get_notifications(self, account_id):
        try:
            sql = "UPDATE notifications SET status = %s WHERE account_id = %s"
            self.mycursor.execute(sql, (1, account_id))
            # Commit the changes to the database
            self.mydb.commit()
            sql = "SELECT notification_message, notification_date, status FROM notifications WHERE account_id = %s"
            self.mycursor.execute(sql, (account_id,))
             # Fetch all rows from the result set
            notifications_data = self.mycursor.fetchall()
            
            # Check if any rows were returned
            if notifications_data:
                # Construct a list of dictionaries containing review details
                notifications = [{
                    'notification_message': row[0],
                    'notification_date': row[1],
                    'status': row[2],
                } for row in notifications_data]
                return notifications
            else:
                # Return an empty list if no notifications are found
                return []
        except Exception as e:
            print(f"An error occurred while getting unread notification count: {str(e)}")
            return []  # Return an empty list in case of any error


