from flask import Flask, request
from request_handler import RequestHandler

# Create a Flask application
app = Flask(__name__)

handler = RequestHandler()

# Define a route for handling GET requests
@app.route('/', methods=['GET'])
def index():
    return 'Hello, World! This is the index page.'

# Define a route for handling POST requests
@app.route('/signup', methods=['POST'])
def signup():
    handler.handle_signup(request.form)
    return f'The submitted data is: {request.form}'

# Define a route for handling POST requests
@app.route('/login', methods=['POST'])
def login():
    handler.handle_login(request.form)
    return f'The submitted data is: {request.form}'


if __name__ == '__main__':
    # Run the Flask application in debug mode on localhost (port 5000)
    app.run(host='0.0.0.0', port=8080, debug=True)
