from flask import Flask
from config import Config
from flask_cors import CORS
from extensions import db, migrate, bcrypt, jwt
from seed_data import seed_cli 
from routes.progress import progress_bp


app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/*": {"origins": "*"}})

# инициализация расширений
db.init_app(app)
migrate.init_app(app, db)   # 👈 обязательно!
bcrypt.init_app(app)
jwt.init_app(app)
app.cli.add_command(seed_cli)
@app.route("/")
def home():
    return "Flask работает!"

from routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix="/auth")

from routes.flashcards import flashcards_bp
app.register_blueprint(flashcards_bp, url_prefix="/flashcards")

#from routes.categories import categories_bp
#app.register_blueprint(categories_bp, url_prefix="/categories")

from routes.repetition import repetition_bp
app.register_blueprint(repetition_bp, url_prefix="/repetition")

from routes.progress import progress_bp
app.register_blueprint(progress_bp, url_prefix="/progress")

if __name__ == "__main__":
    app.run(debug=True)


