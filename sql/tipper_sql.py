import mysql.connector
import time
from datetime import datetime
with open('../sql_password.txt') as f:
    sql_password = f.read()

mydb = mysql.connector.connect(user='root', password=sql_password,
                              host='localhost',
                              auth_plugin='mysql_native_password',database='nano_tipper_z')
mycursor = mydb.cursor()


def init_db():
    mycursor.execute("CREATE DATABASE nano_tipper_z")
    mydb.commit()


def init_history():
    mycursor.execute("CREATE TABLE history ("
                        "id INT AUTO_INCREMENT PRIMARY KEY, "
                        "username VARCHAR(255), "
                        "action VARCHAR(255), "
                        "reddit_time TIMESTAMP, "
                        "sql_time TIMESTAMP, "
                        "address VARCHAR(255), "
                        "comment_or_message VARCHAR(255), "
                        "recipient_username VARCHAR(255), "
                        "recipient_address VARCHAR(255), "
                        "amount VARCHAR(255), "
                        "hash VARCHAR(255), "
                        "comment_id VARCHAR(255), "
                        "comment_text VARCHAR(255), "
                        "notes VARCHAR(255)"
                     ")"
                     )
    mydb.commit()


def init_messages():
    mycursor.execute("CREATE TABLE messages ("
                        "id INT AUTO_INCREMENT PRIMARY KEY, "
                        "username VARCHAR(255), "
                        "subject VARCHAR(255), "
                        "message VARCHAR(5000) "
                     ")"
                     )
    mydb.commit()


def init_accounts():
    mycursor.execute("CREATE TABLE accounts ("
                        "username VARCHAR(255) PRIMARY KEY, "
                        "address VARCHAR(255), "
                        "private_key VARCHAR(255), "
                        "key_released BOOL, "
                        "minimum VARCHAR(255), "
                        "notes VARCHAR(255), "
                        "auto_receive BOOL, "
                        "silence BOOL, "
                        "active BOOL"
                     ")"
                     )
    mydb.commit()


def init_subreddits():
    mycursor.execute("CREATE TABLE subreddits ("
                        "subreddit VARCHAR(255) PRIMARY KEY, "
                        "reply_to_comments BOOL, "
                        "footer VARCHAR(255), "
                        "status VARCHAR(255) "
                     ")"
                     )
    mydb.commit()


def history(num_records):
    mycursor.execute('SHOW COLUMNS FROM history')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)
    mycursor.execute("SELECT * FROM history ORDER BY id DESC limit %s" % num_records)
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

def messages():
    mycursor.execute('SHOW COLUMNS FROM messages')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM messages")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def accounts():
    mycursor.execute('SHOW COLUMNS FROM accounts')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM accounts")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def subreddits():
    mycursor.execute('SHOW COLUMNS FROM subreddits')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM subreddits")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def list_columns():
    mycursor.execute('SHOW COLUMNS FROM history')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)
    print("*****")
    mycursor.execute('SHOW COLUMNS FROM accounts')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def allowed_request(username, seconds=30, num_requests=5):
    """
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """
    sql = 'SELECT sql_time FROM history WHERE username=%s'
    val = (username, )
    mycursor.execute(sql, val)
    myresults = mycursor.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        print(myresults[-5][0], datetime.fromtimestamp(time.time()))
        print((datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds())
        return (datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds() > seconds


def delete_user(username):
    sql = 'DELETE FROM accounts WHERE username = %s'
    val = (username, )
    mycursor.execute(sql, val)
    mydb.commit()


def add_subreddit(subreddit, reply_to_comments, footer, status):
    sql = "INSERT INTO subreddits (subreddit, reply_to_comments, footer, status) VALUES (%s, %s, %s, %s)"
    val = (subreddit, reply_to_comments, footer, status, )
    mycursor.execute(sql, val)
    mydb.commit()
#accounts()
#subreddits()
#history(30)
#messages()







# sql = "UPDATE subreddits SET status = 'friendly' WHERE subreddit = 'nano_tipper_z'"
# mycursor.execute(sql)
# mydb.commit()

# add_subreddit('nanocurrency', True, None, 'friendly')
# add_subreddit('cryptocurrency247', True, None, 'friendly')
# add_subreddit('nanotrade', True, None, 'friendly')
# add_subreddit('do_not_post_here', True, None, 'hostile')




#history(30)
#messages()
#print("************************************************************")
#accounts()

#print(allowed_request('zily88', 30, 5))
#delete_user('nano_tipper_z_test2')

subreddits()
