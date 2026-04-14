from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

engine = create_engine("mysql://root:cset155@localhost/boatdb", echo=True)

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (email, password) VALUES (:email, :password)"),
                         {"email": email, "password": password})

        return redirect(url_for('login'))

    return render_template('signup.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with engine.begin() as conn:
            user = conn.execute(text("SELECT * FROM users WHERE email=:email"),
                                {"email": email}).fetchone()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            return redirect(url_for('get_boats'))

        return "Invalid login"

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ---------------- BOATS ----------------
@app.route('/boats')
def get_boats():
    with engine.begin() as conn:
        boats = conn.execute(text("SELECT * FROM boats")).fetchall()

    return render_template('boats.html', boats=boats)

# ---------------- CREATE ----------------
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO boats (name, type, owner_id, rental_price)
                VALUES (:name, :type, :owner_id, :rental_price)
            """), request.form)

        return redirect(url_for('get_boats'))

    return render_template('create.html')

# ---------------- DETAIL ----------------
@app.route('/boat/<int:id>')
def boat_detail(id):
    with engine.begin() as conn:
        boat = conn.execute(text("SELECT * FROM boats WHERE id=:id"), {"id": id}).fetchone()

    if not boat:
        return render_template('error.html', message="Boat not found")

    return render_template('boat_detail.html', boat=boat)

# ---------------- UPDATE ----------------
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    with engine.begin() as conn:
        boat = conn.execute(text("SELECT * FROM boats WHERE id=:id"), {"id": id}).fetchone()

    if request.method == 'POST':
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE boats
                SET name=:name, type=:type, owner_id=:owner_id, rental_price=:rental_price
                WHERE id=:id
            """), {**request.form, "id": id})

        return redirect(url_for('boat_detail', id=id))

    return render_template('update.html', boat=boat)

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM boats WHERE id=:id"), {"id": id})

    return redirect(url_for('get_boats'))

# ---------------- SEARCH ----------------
@app.route('/search')
def search():
    q = request.args.get('q', '')

    with engine.begin() as conn:
        results = conn.execute(text("""
            SELECT * FROM boats
            WHERE name LIKE :q OR type LIKE :q
        """), {"q": f"%{q}%"}).fetchall()

    return render_template('search.html', results=results, q=q)

if __name__ == '__main__':
    app.run(debug=True)