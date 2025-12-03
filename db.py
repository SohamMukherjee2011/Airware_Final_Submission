import mysql.connector
import os
import dotenv
dotenv.load_dotenv()
host = os.getenv("DATABASE_HOST")
user = os.getenv("DATABASE_USER")
password = os.getenv("DATABASE_PASSWORD")
database = os.getenv("DATABASE_NAME")
try:
    mydb = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    
    cursor = mydb.cursor()

except :
    print("Database connection error")
    raise
def config():
    dbList = []
    cursor.execute('SHOW DATABASES')
    for x in cursor:
        dbList.append(x[0])
        if "CAPSTONE" not in dbList:
            cursor.execute("CREATE DATABASE CAPSTONE")
            cursor.execute("USE CAPSTONE")
            cursor.execute("""CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(150) NOT NULL,
    first_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    password VARCHAR(255) NULL,
    location VARCHAR(255) NULL,

    route_start_lat DECIMAL(10,7) NULL,
    route_start_lng DECIMAL(10,7) NULL,
    route_end_lat DECIMAL(10,7) NULL,
    route_end_lng DECIMAL(10,7) NULL,

    age_group ENUM('child','teen','adult','senior') NULL,
    is_sensitive TINYINT(1) NULL,
    morning_summary TINYINT(1) NULL DEFAULT 0,
    threshold_alerts TINYINT(1) NULL DEFAULT 0,
    commute_alerts TINYINT(1) NULL DEFAULT 0,
    enable_notifications TINYINT(1) NULL DEFAULT 1,

    PRIMARY KEY (id),
    UNIQUE KEY (email)
)""")
    print('config complete')


def showField(field, value):
    global cursor
    sql = "SELECT username, email, first_name, last_name, password, age_group, is_sensitive, location, route_start_lat, route_start_lng, route_end_lat, route_end_lng  FROM users WHERE " + field + "='" + value + "';"
    cursor.execute(sql)
    valuelist = cursor.fetchall()
    return valuelist
def signupInsert(username, email, password, fname, lname):
    sql = """
        INSERT INTO users (username, email, password, first_name, last_name)
        VALUES (%s, %s, %s, %s, %s)
    """
    val = (username, email, password, fname, lname)

    cursor.execute(sql, val)
    mydb.commit()
def updateOnboarding(user_id, location, age_group, is_sensitive,
                     morning_summary, threshold_alerts, commute_alerts,
                     enable_notifications, route_start_lat, route_start_lng, 
           route_end_lat, route_end_lng):

    sql = """
    UPDATE users
    SET location=%s,
        age_group=%s,
        is_sensitive=%s,
        morning_summary=%s,
        threshold_alerts=%s,
        commute_alerts=%s,
        enable_notifications=%s,
        route_start_lat=%s,
        route_start_lng=%s ,     
        route_end_lat=%s,
        route_end_lng=%s 
    WHERE username=%s
    """

    val = (location, age_group, is_sensitive,
           morning_summary, threshold_alerts,
           commute_alerts, enable_notifications,
           route_start_lat, route_start_lng, 
           route_end_lat, route_end_lng,
           user_id)
    print("start lat:", route_start_lat, type(route_start_lat))
    print("start lng:", route_start_lng, type(route_start_lng))

    cursor.execute(sql, val)
    mydb.commit()

