import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="OmOm1989!!",
    database="shopping_app"
)
cursor = db.cursor(dictionary=True)
