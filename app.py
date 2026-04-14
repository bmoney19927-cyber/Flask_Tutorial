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


# ================= SIGNUP =================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO users (email, password, is_admin)
                VALUES (:email, :password, 0)
            """), {"email": email, "password": password})

        return redirect(url_for('login'))

    return render_template('signup.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with engine.begin() as conn:
            user = conn.execute(text("""
                SELECT * FROM users WHERE email = :email
            """), {"email": email}).fetchone()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['is_admin'] = user.is_admin
            return redirect(url_for('get_boats'))

        return render_template('error.html', message="Invalid login")

    return render_template('login.html')


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ================= BOATS (ALL USERS) =================
@app.route('/boats')
def get_boats():
    with engine.begin() as conn:
        result = conn.execute(text("SELECT * FROM boats")).mappings().all()

    boats = [dict(row) for row in result]

    return render_template('boats.html', boats=boats)



# ================= SEARCH =================
@app.route('/search')
def search():
    q = request.args.get('q', '')

    with engine.begin() as conn:
        results = conn.execute(text("""
            SELECT * FROM boats
            WHERE name LIKE :q OR type LIKE :q
        """), {"q": f"%{q}%"}).fetchall()

    return render_template('search.html', results=results, q=q)


# ================= BOAT DETAIL =================
@app.route('/boat/<int:id>')
def boat_detail(id):
    with engine.begin() as conn:
        boat = conn.execute(text("SELECT * FROM boats WHERE id = :id"), {"id": id}).fetchone()

    if not boat:
        return render_template('error.html', message="Boat not found")

    return render_template('boat_detail.html', boat=boat)


# ================= ADMIN DASHBOARD =================
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return render_template('error.html', message="Access denied")

    with engine.begin() as conn:
        users = conn.execute(text("SELECT * FROM users")).fetchall()
        boats = conn.execute(text("SELECT * FROM boats")).fetchall()

    return render_template('admin.html', users=users, boats=boats)


# ================= ADMIN: ADD BOAT =================
@app.route('/admin/add_boat', methods=['GET', 'POST'])
def admin_add_boat():
    if not session.get('is_admin'):
        return render_template('error.html', message="Access denied")

    if request.method == 'POST':
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO boats (name, type, owner_id, rental_price)
                VALUES (:name, :type, :owner_id, :rental_price)
            """), request.form)

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_add_boat.html')


# ================= ADMIN: EDIT BOAT =================
@app.route('/admin/edit_boat/<int:id>', methods=['GET', 'POST'])
def admin_edit_boat(id):
    if not session.get('is_admin'):
        return render_template('error.html', message="Access denied")

    with engine.begin() as conn:
        boat = conn.execute(text("SELECT * FROM boats WHERE id=:id"), {"id": id}).fetchone()

    if request.method == 'POST':
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE boats
                SET name=:name,
                    type=:type,
                    owner_id=:owner_id,
                    rental_price=:rental_price
                WHERE id=:id
            """), {
                "id": id,
                "name": request.form['name'],
                "type": request.form['type'],
                "owner_id": request.form['owner_id'],
                "rental_price": request.form['rental_price']
            })

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit_boat.html', boat=boat)


# ================= ADMIN: DELETE BOAT =================
@app.route('/admin/delete_boat/<int:id>', methods=['POST'])
def admin_delete_boat(id):
    if not session.get('is_admin'):
        return render_template('error.html', message="Access denied")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM boats WHERE id=:id"), {"id": id})

    return redirect(url_for('admin_dashboard'))


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)