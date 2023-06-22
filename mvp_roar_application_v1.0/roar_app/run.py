# Run file for flask application

# import packages for application run file, will serve using waitress (VM behind FW)
import os
from waitress import serve # use to serve on local host
from app import app

# Launch application

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 8080))
	serve(app, host='127.0.0.1', port=port) #app served on 127.0.0.1:8080
