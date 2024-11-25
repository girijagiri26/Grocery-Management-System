from flask import Flask, render_template, request, redirect, url_for, flash, Response
import mysql.connector
import pdfkit  # Install pdfkit if not already installed (e.g., `pip install pdfkit`)
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'girija@232018',
    'database': 'store'
}

# Function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Products (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
            conn.commit()
            flash('Product added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('products'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('products.html', products=products)

@app.route('/place_order', methods=['GET', 'POST'])
def place_order():
    if request.method == 'POST':
        customer = request.form['customer']
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert the new order
            cursor.execute("INSERT INTO Orders (customer, total) VALUES (%s, %s)", (customer, 0))
            order_id = cursor.lastrowid
            
            # Calculate total
            cursor.execute("SELECT price, stock FROM Products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            price = product[0]
            current_stock = product[1]

            # Check stock
            if current_stock >= int(quantity):
                total = price * int(quantity)
                cursor.execute("INSERT INTO OrderItems (order_id, product_id, quantity) VALUES (%s, %s, %s)", (order_id, product_id, quantity))
                cursor.execute("UPDATE Orders SET total = total + %s WHERE id = %s", (total, order_id))
                new_stock = current_stock - int(quantity)
                cursor.execute("UPDATE Products SET stock = %s WHERE id = %s", (new_stock, product_id))
                conn.commit()
                flash('Order placed successfully!', 'success')
            else:
                flash('Error: Not enough stock available.', 'danger')
                
        except Exception as e:
            conn.rollback()
            flash('Error: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('place_order'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('place_order.html', products=products)

@app.route('/list_orders')
def list_orders():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Updated query to include product name
    cursor.execute("""
        SELECT o.id, o.customer, oi.product_id, p.name AS product_name, oi.quantity, (oi.quantity * p.price) AS total, o.order_date
        FROM Orders o
        JOIN OrderItems oi ON o.id = oi.order_id
        JOIN Products p ON oi.product_id = p.id
    """)
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    # Debugging: Print the orders to check the result
    print(orders)  # Check if product_name is included

    return render_template('list_orders.html', orders=orders)



# Function to get order details by ID
def get_order_by_id(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Orders WHERE id = %s", (order_id,))
    order = cursor.fetchone()  # Fetch the order details
    cursor.close()
    conn.close()
    return order


# Function to update an order
def update_order(order_id, customer_name, product_name, quantity):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Step 1: Check if product_name exists in Products table
    cursor.execute("SELECT id FROM Products WHERE name = %s", (product_name,))
    product = cursor.fetchone()
    
    if product is None:
        flash('Error: Product name does not exist.', 'danger')
        return

    product_id = product[0]  # Get the product_id

    try:
        # Step 2: Update OrderItems table with the product_id and quantity
        cursor.execute("""
            UPDATE OrderItems
            SET product_id = %s, quantity = %s
            WHERE order_id = %s
        """, (product_id, quantity, order_id))

        # Step 3: Optionally, update the total price or other order-related fields
        cursor.execute("""
            UPDATE Orders
            SET total = (SELECT SUM(oi.quantity * p.price) FROM OrderItems oi
                         JOIN Products p ON oi.product_id = p.id WHERE oi.order_id = %s)
            WHERE id = %s
        """, (order_id, order_id))

        conn.commit()
        flash('Order updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

@app.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    order = get_order_by_id(order_id)  # Fetch order details from the database using the order_id
    
    if request.method == 'POST':
        customer_name = request.form['customerName']  # Access the 'customerName' field
        product = request.form['product']
        quantity = request.form['quantity']
        
        # Update order in the database (e.g., update the order details based on order_id)
        update_order(order_id, customer_name, product, quantity)
        
        return redirect(url_for('list_orders'))  # Redirect to the list of orders after saving changes
    
    return render_template('edit_order.html', order=order)  # Render the form with the order data



@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Deleting related order items first
        cursor.execute("DELETE FROM OrderItems WHERE order_id = %s", (order_id,))
        # Deleting the order
        cursor.execute("DELETE FROM Orders WHERE id = %s", (order_id,))
        conn.commit()
        flash('Order deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error: ' + str(e), 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('list_orders'))



@app.route('/generate_bill/<int:order_id>')
def generate_bill(order_id):
    # Connect to the database and fetch order details
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the order data
    cursor.execute("SELECT * FROM Orders WHERE id = %s", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        flash('Order not found!', 'danger')
        return redirect(url_for('list_orders'))
    
    # Fetch the order items
    cursor.execute("SELECT Products.name, OrderItems.quantity, Products.price FROM OrderItems "
                   "JOIN Products ON OrderItems.product_id = Products.id WHERE OrderItems.order_id = %s", (order_id,))
    order_items = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Get the current date and time
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prepare the data for the PDF (use HTML template to format the bill)
    rendered = render_template('bill_template.html', order=order, order_items=order_items, current_datetime=current_datetime)

    # Generate the PDF
    pdf = pdfkit.from_string(rendered, False)

    # Send the PDF as a response
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=bill_{order_id}.pdf'})

@app.route('/edit_product/<int:product_id>', methods=['GET'])
def edit_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch product details, including stock
    cursor.execute("SELECT id, name, price, stock FROM Products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('products'))
    
    return render_template('edit_product.html', product=product)

@app.route('/update_product/<int:product_id>', methods=['POST'])
def update_product(product_id):
    name = request.form['name']
    price = request.form['price']
    stock = request.form['stock']  # Fetch the stock field from the form
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update product details, including stock
    cursor.execute("""
        UPDATE Products
        SET name = %s, price = %s, stock = %s
        WHERE id = %s
    """, (name, price, stock, product_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Product updated successfully!', 'success')
    return redirect(url_for('products'))


if __name__ == '__main__':
    app.run(debug=True)


