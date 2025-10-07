from flask import Flask, render_template, request, redirect, url_for
from db_config import get_db_connection

app = Flask(__name__)

@app.route('/')
def index():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/needs')
def view_needs():
    """Displays a list of all needs from all orphanages."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # SQL query to get needs along with orphanage name and item category name
        query = """
            SELECT 
                o.name AS orphanage_name,
                ic.category_name,
                n.required_qty
            FROM Need n
            JOIN Orphanage o ON n.orphanage_id = o.orphanage_id
            JOIN ItemCategory ic ON n.category_id = ic.category_id
            ORDER BY o.name;
        """
        cursor.execute(query)
        needs_data = cursor.fetchall()
        
        return render_template('needs.html', needs=needs_data)
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/dashboard/<int:orphanage_id>')
def dashboard(orphanage_id):
    """Renders the smart dashboard for a specific orphanage."""
    # In a real app, orphanage_id would come from a user login session.
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get orphanage name
        cursor.execute("SELECT name FROM Orphanage WHERE orphanage_id = %s", (orphanage_id,))
        orphanage = cursor.fetchone()

        # 2. Get key numbers (child count, staff count)
        cursor.execute("SELECT COUNT(*) AS count FROM Children WHERE orphanage_id = %s", (orphanage_id,))
        child_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) AS count FROM Staff WHERE orphanage_id = %s", (orphanage_id,))
        staff_count = cursor.fetchone()['count']
        
        # 3. Get critical needs alerts
        query_needs = """
            SELECT ic.category_name, i.quantity, n.required_qty
            FROM Inventory i
            JOIN Need n ON i.category_id = n.category_id AND i.orphanage_id = n.orphanage_id
            JOIN ItemCategory ic ON i.category_id = ic.category_id
            WHERE i.orphanage_id = %s AND i.quantity < n.required_qty
        """
        cursor.execute(query_needs, (orphanage_id,))
        critical_needs = cursor.fetchall()

        # 4. Get recent donations
        query_donations = """
            SELECT d.name, dn.donation_date, dn.cash_amount 
            FROM Donation dn 
            JOIN Donor d ON dn.donor_id = d.donor_id
            WHERE dn.target_orphanage_id = %s 
            ORDER BY dn.donation_date DESC LIMIT 5
        """
        cursor.execute(query_donations, (orphanage_id,))
        recent_donations = cursor.fetchall()

        return render_template('dashboard.html', 
                               orphanage=orphanage,
                               child_count=child_count,
                               staff_count=staff_count,
                               critical_needs=critical_needs,
                               recent_donations=recent_donations)
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- Placeholder Routes for Future Implementation ---

@app.route('/donate/<int:orphanage_id>/<int:category_id>')
def donate_form(orphanage_id, category_id):
    # This will render the pre-filled donation form
    # TODO: Fetch orphanage and category details to show on the form
    return "This is where the donation form will be. (To be implemented)"

@app.route('/submit_donation', methods=['POST'])
def submit_donation():
    # This will handle the logic for inserting donation data into the database
    # TODO: Get data from request.form and execute INSERT queries
    return "Donation submitted! (To be implemented)"

@app.route('/track')
def track_form():
    # This will render the page with a form to enter a donation_id
    # TODO: Create track.html
    return "This is the donation tracking form. (To be implemented)"

if __name__ == '__main__':
    app.run(debug=True) # debug=True allows you to see errors and auto-reloads the server