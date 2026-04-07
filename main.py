from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import Column, Integer, String, Numeric, create_engine, text

def row_to_dict(row):
    """Convert SQLAlchemy Row object to dictionary"""
    if row is None:
        return None
    return dict(row._mapping)

app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/boatdb"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()


# render a file
@app.route('/')
def index():
    return render_template('index.html')


# remember how to take user inputs?
@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


# get all boats with optional sorting and filtering
@app.route('/boats')
@app.route('/boats/')
@app.route('/boats/<int:page>')
def get_boats(page=1):
    per_page = 10
    
    # Get query parameters for filtering and sorting
    sort_by = request.args.get('sort_by', 'id')  # id, name, rental_price
    boat_type = request.args.get('boat_type', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    
    # Validate sort_by
    if sort_by not in ['id', 'name', 'rental_price']:
        sort_by = 'id'
    
    # Build the WHERE clause
    where_clause = "WHERE 1=1"
    params = {}
    
    if boat_type:
        where_clause += " AND type = :boat_type"
        params['boat_type'] = boat_type
    
    if min_price:
        try:
            where_clause += " AND rental_price >= :min_price"
            params['min_price'] = float(min_price)
        except ValueError:
            pass
    
    if max_price:
        try:
            where_clause += " AND rental_price <= :max_price"
            params['max_price'] = float(max_price)
        except ValueError:
            pass
    
    # Get filtered boats
    total_query = f"SELECT COUNT(*) as count FROM boatdb {where_clause}"
    total_result = conn.execute(text(total_query), params).fetchone()
    total_boats = total_result[0] if total_result else 0
    
    query = f"SELECT * FROM boatdb {where_clause} ORDER BY {sort_by} LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    boats_result = conn.execute(text(query), params).all()
    boats = [row_to_dict(row) for row in boats_result]
    
    # Get unique boat types for filter dropdown
    boat_types_result = conn.execute(text("SELECT DISTINCT type FROM boatdb")).all()
    boat_types = [row_to_dict(row) for row in boat_types_result]
    
    return render_template('boats.html', boats=boats, page=page, per_page=per_page, 
                         sort_by=sort_by, boat_type=boat_type, min_price=min_price, 
                         max_price=max_price, boat_types=boat_types, total_boats=total_boats)


# search boats
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    search_query = ''
    search_type = 'name'  # default search type
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        search_type = request.form.get('search_type', 'name')
        
        if search_query:
            if search_type == 'id':
                try:
                    boat_id = int(search_query)
                    results_raw = conn.execute(text(f"SELECT * FROM boatdb WHERE id = :boat_id"), 
                                         {'boat_id': boat_id}).all()
                    results = [row_to_dict(row) for row in results_raw]
                except ValueError:
                    pass
            elif search_type == 'name':
                results_raw = conn.execute(text(f"SELECT * FROM boatdb WHERE name LIKE :search_query"),
                                     {'search_query': f"%{search_query}%"}).all()
                results = [row_to_dict(row) for row in results_raw]
            elif search_type == 'type':
                results_raw = conn.execute(text(f"SELECT * FROM boatdb WHERE type LIKE :search_query"),
                                     {'search_query': f"%{search_query}%"}).all()
                results = [row_to_dict(row) for row in results_raw]
    
    return render_template('search.html', results=results, search_query=search_query, 
                         search_type=search_type)


# get boat details
@app.route('/boat/<int:boat_id>')
def boat_detail(boat_id):
    boat = conn.execute(text(f"SELECT * FROM boatdb WHERE id = :boat_id"), 
                       {'boat_id': boat_id}).fetchone()
    if boat is None:
        return render_template('error.html', message="Boat not found"), 404
    boat = row_to_dict(boat)
    return render_template('boat_detail.html', boat=boat)


# create boat (read/write)
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        boat_type = request.form.get('type')
        owner_id = request.form.get('owner_id')
        rental_price = request.form.get('rental_price')
        
        if name and boat_type and owner_id and rental_price:
            conn.execute(text("INSERT INTO boatdb (name, type, owner_id, rental_price) VALUES (:name, :type, :owner_id, :rental_price)"),
                        {'name': name, 'type': boat_type, 'owner_id': int(owner_id), 'rental_price': float(rental_price)})
            conn.commit()
            return redirect(url_for('get_boats'))
    
    return render_template('create.html')


# delete boat
@app.route('/delete/<int:boat_id>', methods=['POST'])
def delete_boat(boat_id):
    boat = conn.execute(text(f"SELECT * FROM boatdb WHERE id = :boat_id"), 
                       {'boat_id': boat_id}).fetchone()
    if boat is None:
        return render_template('error.html', message="Boat not found"), 404
    
    conn.execute(text(f"DELETE FROM boatdb WHERE id = :boat_id"), {'boat_id': boat_id})
    conn.commit()
    return redirect(url_for('get_boats'))


# update boat
@app.route('/update/<int:boat_id>', methods=['GET', 'POST'])
def update_boat(boat_id):
    boat_row = conn.execute(text(f"SELECT * FROM boatdb WHERE id = :boat_id"), 
                       {'boat_id': boat_id}).fetchone()
    if boat_row is None:
        return render_template('error.html', message="Boat not found"), 404
    
    boat = row_to_dict(boat_row)
    
    if request.method == 'POST':
        name = request.form.get('name', boat['name'])
        boat_type = request.form.get('type', boat['type'])
        owner_id = request.form.get('owner_id', boat['owner_id'])
        rental_price = request.form.get('rental_price', boat['rental_price'])
        
        conn.execute(text("UPDATE boatdb SET name = :name, type = :type, owner_id = :owner_id, rental_price = :rental_price WHERE id = :boat_id"),
                    {'name': name, 'type': boat_type, 'owner_id': int(owner_id), 'rental_price': float(rental_price), 'boat_id': boat_id})
        conn.commit()
        return redirect(url_for('boat_detail', boat_id=boat_id))
    
    return render_template('update.html', boat=boat)



if __name__ == '__main__':
    app.run(debug=True)
