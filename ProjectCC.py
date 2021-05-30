from pydoc import render_doc
from flask import Flask, render_template, request, redirect
# from matplotlib.style import use
from pymysql import connections
import os
import boto3
from config import *
from sns import *

app = Flask(__name__, template_folder='./frontend/templates',static_folder='./frontend/static')

sns_wrapper = SnsWrapper(boto3.resource('sns', region_name="us-east-1"))

topic_name = 'projectCC'

print(f"Creating topic {topic_name}.")
topic = sns_wrapper.create_topic(topic_name)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)

@app.route("/index.html", methods=['GET'])
def home():
    return render_template("index.html")

@app.route("/", methods=['GET'])
def home_simple():
    return render_template("index.html")

@app.route("/register.html", methods=['GET'])
def register():
    return render_template('register.html')

@app.route("/login.html", methods=['GET'])
def login():
    return render_template('login.html')

@app.route("/about.html", methods=['GET'])
def about():
    return render_template('about.html')

@app.route("/register", methods=['POST'])
def Register():
    last_name = request.form['lname']
    first_name = request.form['fname']
    address = request.form['address']
    phone = request.form['phone']    
    email = request.form['email']    
    password = request.form['password']
    image = request.files['image']

    if image.filename == "":
            return "Please select a file"

    insert_sql = "INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=%s", email)
    out = cursor.fetchone()

    if out == None:
    
        email_sub = sns_wrapper.subscribe(topic, 'email', email)
        
        while (email_sub.attributes['PendingConfirmation'] == 'true'):
            email_sub.reload()

        try:
            cursor.execute(insert_sql, ('', first_name, last_name, address, phone, email, password))
            db_conn.commit()

            image_file_name_in_s3 = "user_" + last_name + "_" + first_name + "_image_file"
            s3 = boto3.resource('s3')

            try:
                print("Data inserted in MySQL RDS... uploading image to S3...")
                s3.Bucket(custombucket).put_object(Key=image_file_name_in_s3, Body=image)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    image_file_name_in_s3)

            except Exception as e:
                return str(e)

        finally:
            cursor.close()
    else:
        return render_template('register.html', text="This email is already in our database.")

    return render_template('index.html')

@app.route("/login", methods=['POST', 'GET'])
def Login():
    email = request.form['email']    
    password = request.form['password']
    cursor = db_conn.cursor()
    # cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s;", (email,password,))
    cursor.execute("SELECT * FROM users WHERE email=%s AND password =%s", (email, password))
    out = cursor.fetchone()

    if out == None:
        return render_template('login.html', text="Email or password is wrong. Please try again!")
    else:
        return redirect('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
