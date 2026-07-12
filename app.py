import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

from models import db
db.init_app(app)

with app.app_context():
    from models import User, Transaction, CategoryRule
    db.create_all()
    from services.categorizer import load_default_rules
    load_default_rules()

from routes.main import main_bp
from routes.auth import auth_bp
from routes.api import api_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
