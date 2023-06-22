# Import flask module, initialize application
from flask import Flask
from datetime import timedelta

# Define app function
app = Flask(__name__, instance_relative_config=True)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes = 720) #sets max session to 12 hours

# Import views
from app import views

# Load config file
app.config.from_object('config')
