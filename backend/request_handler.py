import urllib.parse
import json
import mysql.connector
import hashlib
import os
from datetime import datetime, timedelta


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
        # hashed_password = self.hash_password(password)
        
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
        sql = "INSERT INTO Accounts (email, password, first_name, last_name, address, account_type,birth_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (email, password, first_name, last_name, address, account_type,birth_date)
        self.mycursor.execute(sql, val)
        self.mydb.commit()
        return {'success': 'SignUp successful'}
        
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
        self.mycursor.execute("SELECT subjects.subject_id, subjects.title, subjects.content, subjects.account_id, COUNT(comments.subject_id) AS comment_count FROM subjects LEFT JOIN comments ON subjects.subject_id = comments.subject_id GROUP BY subjects.subject_id ORDER BY subjects.date_and_time DESC")
        # Fetch all subjects from the result set
        list_subjects = self.mycursor.fetchall()
        subjects = [{'subject_id': row[0], 'title': row[1], 'content': row[2], 'account_id': row[3], 'comment_count': row[4]} for row in list_subjects]
        # print("Fetched subjects:", subjects)  # Print fetched subjects
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

        where = 'WHERE (a.date BETWEEN %s AND %s)'
        val = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

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
                       
        current_date = datetime.today()
        
        schedule = self.list_work_schedule(current_date, current_date+timedelta(days=31))

        result = dict()
        for i in range(31):
            iteration_date = (current_date + timedelta(days=i)).date()

            day_availability = dict()
            
            # filter out all rows that don't have our iteration date
            relevant_rows = filter(lambda row: row[1] == iteration_date, schedule)

            # for each of the rows with our date, extract employee id and place it in the correct hour key
            for row in relevant_rows:
                hour = row[2]['hour']

                if hour not in day_availability:
                    day_availability[hour] = []
                
                day_availability[hour].append(row[4])

            result[iteration_date] = day_availability
        
        return result