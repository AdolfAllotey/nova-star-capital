from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "change_this_secret_key"  # à sécuriser

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simplicité : utilisateur hardcodé
users = {
    "admin": {"password": "motdepasse"}
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Identifiants invalides")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    # Exemple données dynamiques
    data = {
        "positions": [
            {"token": "BTC", "amount": 0.5, "value_usd": 20000},
            {"token": "ETH", "amount": 2, "value_usd": 3500},
        ],
        "performance": {
            "daily_change": 1.5,
            "monthly_change": 10.2
        }
    }
    return render_template("dashboard.html", data=data, user=current_user)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8501)