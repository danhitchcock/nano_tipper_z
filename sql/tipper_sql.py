import mysql.connector

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


def init_accounts():
    mycursor.execute("CREATE TABLE accounts ("
                        "username VARCHAR(255) PRIMARY KEY, "
                        "address VARCHAR(255), "
                        "private_key VARCHAR(255), "
                        "key_released BOOL, "
                        "minimum VARCHAR(255), "
                        "notes VARCHAR(255), "
                        "auto_receive BOOL"
                     ")"
                     )
    mydb.commit()


def history():
    mycursor.execute('SHOW COLUMNS FROM history')
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)
    mycursor.execute("SELECT * FROM history")
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

history()
print("************************************************************")
accounts()

def delete_user(username):
    sql = 'DELETE FROM accounts WHERE username = %s'
    val = (username, )
    mycursor.execute(sql, val)
    mydb.commit()

history()
print("************************************************************")
accounts()



