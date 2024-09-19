from .base_settings import *

# Production settings
DEBUG = False

# Change this before deploying!
SECRET_KEY = "CHANGE_ME"

# Directory where static files will be served from. Should be accessible for your Webserver
STATIC_ROOT = "/var/www/example.com/static/"

# Set all hosts your deploy will be available from
ALLOWED_HOSTS = []

# Configure your space
SPACE_STATE_SECRET = ""
SPACE_NAME = ""
SPACE_CONTACT = ""