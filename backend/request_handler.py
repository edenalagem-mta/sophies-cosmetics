import urllib.parse
import json
import mysql.connector
import hashlib


class RequestHandler(object):
    def __init__(self) -> None:
         pass
        # self.mydb = mysql.connector.connect(
        #                 host="your_mysql_host",
        #                 user="your_mysql_user",
        #                 password="your_mysql_password",
        #                 database="your_mysql_database"
        #                 )
        # mycursor = mydb.cursor()
    
    def hash_password(password):
        md5_hash = hashlib.md5(password.encode('utf-8'))
        return md5_hash.hexdigest()

    def handle_signup(self, post_data):
        # Extract parameters from the form data
        email = post_data['email'][0]
        password = post_data['password'][0]
        first_name = post_data['first_name'][0]
        last_name = post_data['last_name'][0]
        address = post_data['address'][0]
        account_type = post_data['account_type'][0]

        print(f'handle_signup: {post_data}')

        hashed_password = self.hash_password(password)
        
        #  # Check if email already exists in the database
        # sql = "SELECT * FROM Accounts WHERE email = %s"
        # val = (email,)
        # self.mycursor.execute(sql, val)
        # existing_user = self.mycursor.fetchone()

        # if existing_user:
        #     # Send error response if email already exists
        #     self.send_response(400)
        #     self.send_header('Content-type', 'application/json')
        #     self.end_headers()
        #     response_data = {'error': 'Email address already in use'}
        #     
        #     return
    #     # Insert new user into the database
    #     sql = "INSERT INTO Accounts (email, password, first_name, last_name, address, accountType) VALUES (%s, %s, %s, %s, %s, %s)"
    #     val = (email, password, first_name, last_name, address, account_type)
    #     self.mycursor.execute(sql, val)
    #     self.mydb.commit()
        # Send success response
        
    def handle_login(self, post_data):
        # Extract parameters from the form data
        email = post_data['email'][0]
        password = post_data['password'][0]

        hashed_password = self.hash_password(password)

