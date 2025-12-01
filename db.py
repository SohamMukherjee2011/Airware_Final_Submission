import mysql.connector

try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Soham@12",
        database="CAPSTONE",
        auth_plugin="mysql_native_password"
    )

    cursor = mydb.cursor()

except :
    print("Database connection error")
    raise

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

