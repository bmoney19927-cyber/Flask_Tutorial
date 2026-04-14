from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey123"

engine = create_engine("mysql://root:cset155@localhost/boatdb", echo=False)


# ================= HOME =================
@app.route('/')
def index():
    return render_template('index.html')


# ================= BOATS (FIXED - MAIN ISSUE) =================
@app.route('/boats')
def get_boats():
    boats = []
    error = None
    
    with engine.begin() as conn:
        # Try boatdb first (where most data is), then boats
        try:
            result = conn.execute(text("SELECT * FROM boatdb")).fetchall()
            boats = [dict(row._mapping) for row in result]
        except Exception as e:
            try:
                result = conn.execute(text("SELECT * FROM boats")).fetchall()
                boats = [dict(row._mapping) for row in result]
            except Exception as e2:
                error = f"Error loading boats: {str(e2)}"
    
    return render_template('boats.html', boats=boats, error=error)


# ================= SEARCH (FIXED) =================
@app.route('/search')
def search():
    q = request.args.get('q', '')

    with engine.begin() as conn:
        try:
            result = conn.execute(text("""
                SELECT * FROM boatdb
                WHERE name LIKE :q OR type LIKE :q
            """), {"q": f"%{q}%"}).fetchall()
        except:
            result = conn.execute(text("""
                SELECT * FROM boats
                WHERE name LIKE :q OR type LIKE :q
            """), {"q": f"%{q}%"}).fetchall()

    results = [dict(row._mapping) for row in result]

    return render_template('search.html', results=results, q=q)


# ================= BOAT DETAIL =================
@app.route('/boat/<int:id>')
def boat_detail(id):
    with engine.begin() as conn:
        try:
            boat = conn.execute(
                text("SELECT * FROM boatdb WHERE id = :id"),
                {"id": id}
            ).fetchone()
        except:
            boat = conn.execute(
                text("SELECT * FROM boats WHERE id = :id"),
                {"id": id}
            ).fetchone()

    if not boat:
        return render_template('error.html', message="Boat not found")

    return render_template('boat_detail.html', boat=dict(boat._mapping))


# ================= CREATE =================
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        with engine.begin() as conn:
            try:
                conn.execute(text("""
                    INSERT INTO boats (name, type, owner_id, rental_price)
                    VALUES (:name, :type, :owner_id, :rental_price)
                """), request.form)
            except:
                conn.execute(text("""
                    INSERT INTO boatdb (name, type, owner_id, rental_price)
                    VALUES (:name, :type, :owner_id, :rental_price)
                """), request.form)

        return redirect(url_for('get_boats'))

    return render_template('create.html')


# ================= DELETE =================
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    with engine.begin() as conn:
        try:
            conn.execute(text("DELETE FROM boats WHERE id = :id"), {"id": id})
        except:
            conn.execute(text("DELETE FROM boatdb WHERE id = :id"), {"id": id})

    return redirect(url_for('get_boats'))


# ================= ADMIN CHECK (SAFE) =================
@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return render_template('error.html', message="Access denied")

    with engine.begin() as conn:
        users = conn.execute(text("SELECT * FROM users")).fetchall()
        boats = conn.execute(text("SELECT * FROM boats")).fetchall()

    return render_template(
        'admin.html',
        users=[dict(u._mapping) for u in users],
        boats=[dict(b._mapping) for b in boats]
    )


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    email = request.form['email']
    password = request.form['password']

    with engine.begin() as conn:
        user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": email}).fetchone()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['email'] = user.email
        # Only admin@boats.com is an admin
        session['is_admin'] = (email == 'admin@boats.com')
        return redirect(url_for('get_boats'))

    return render_template('error.html', message="Invalid login")


# ================= SIGNUP =================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    email = request.form['email']
    password = request.form['password']
    
    # Hash the password
    hashed_password = generate_password_hash(password)
    
    with engine.begin() as conn:
        # Check if user already exists
        existing_user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": email}).fetchone()
        
        if existing_user:
            return render_template('error.html', message="Email already registered")
        
        # Create new user - always set is_admin to 0 for signups
        conn.execute(text("""
            INSERT INTO users (email, password, is_admin)
            VALUES (:email, :password, 0)
        """), {"email": email, "password": hashed_password})
    
    # Automatically log in the new user
    with engine.begin() as conn:
        user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": email}).fetchone()
    
    session['user_id'] = user.id
    session['email'] = user.email
    # Only admin@boats.com is an admin
    session['is_admin'] = (email == 'admin@boats.com')
    
    return redirect(url_for('get_boats'))


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)