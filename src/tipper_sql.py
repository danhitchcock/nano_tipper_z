import time
from datetime import datetime
from translations import database_name, mydb, mycursor


def init_db():
    mycursor.execute("CREATE DATABASE %s" % database_name)
    mydb.commit()


def init_history():
    mycursor.execute(
        "CREATE TABLE history ("
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
        "notes VARCHAR(255), "
        "return_status VARCHAR(255)"
        ")"
    )
    mydb.commit()


def init_messages():
    mycursor.execute(
        "CREATE TABLE messages ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "username VARCHAR(255), "
        "subject VARCHAR(255), "
        "message VARCHAR(5000) "
        ")"
    )
    mydb.commit()


def init_accounts():
    mycursor.execute(
        "CREATE TABLE accounts ("
        "username VARCHAR(255) PRIMARY KEY, "
        "address VARCHAR(255), "
        "private_key VARCHAR(255), "
        "key_released BOOL, "
        "minimum VARCHAR(255), "
        "notes VARCHAR(255), "
        "auto_receive BOOL, "
        "silence BOOL, "
        "active BOOL, "
        "percentage VARCHAR(255)"
        ")"
    )
    mydb.commit()


def init_subreddits():
    mycursor.execute(
        "CREATE TABLE subreddits ("
        "subreddit VARCHAR(255) PRIMARY KEY, "
        "reply_to_comments BOOL, "
        "footer VARCHAR(255), "
        "status VARCHAR(255) "
        ")"
    )
    mydb.commit()


def init_projects():
    mycursor.execute(
        "CREATE TABLE projects ("
        "project VARCHAR(255) PRIMARY KEY, "
        "address VARCHAR(255)"
        ")"
    )
    mydb.commit()


def history(num_records, username=None):
    mycursor.execute("SHOW COLUMNS FROM history")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)
    if username:
        mycursor.execute(
            "SELECT * FROM history WHERE username = '%s' ORDER BY id DESC limit %s"
            % (username, num_records)
        )
    else:
        mycursor.execute(
            "SELECT * FROM history ORDER BY id DESC limit %s" % num_records
        )
    myresult = mycursor.fetchall()
    for result in reversed(myresult):
        print(result)


def messages():
    mycursor.execute("SHOW COLUMNS FROM messages")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM messages")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def accounts():
    mycursor.execute("SHOW COLUMNS FROM accounts")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM accounts")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def subreddits():
    mycursor.execute("SHOW COLUMNS FROM subreddits")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)

    mycursor.execute("SELECT * FROM subreddits")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)


def list_columns():
    mycursor.execute("SHOW COLUMNS FROM history")
    myresult = mycursor.fetchall()
    for result in myresult:
        print(result)
    print("*****")
    mycursor.execute("SHOW COLUMNS FROM accounts")
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
    sql = "SELECT sql_time FROM history WHERE username=%s"
    val = (username,)
    mycursor.execute(sql, val)
    myresults = mycursor.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        print(myresults[-5][0], datetime.fromtimestamp(time.time()))
        print((datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds())
        return (
            datetime.fromtimestamp(time.time()) - myresults[-5][0]
        ).total_seconds() > seconds


def delete_user(username):
    sql = "DELETE FROM accounts WHERE username = %s"
    val = (username,)
    mycursor.execute(sql, val)
    mydb.commit()


def add_subreddit(subreddit, reply_to_comments=True, footer="", status="friendly"):
    sql = "INSERT INTO subreddits (subreddit, reply_to_comments, footer, status) VALUES (%s, %s, %s, %s)"
    val = (subreddit, reply_to_comments, footer, status)
    mycursor.execute(sql, val)
    mydb.commit()


def modify_subreddit(subreddit, status):
    sql = "UPDATE subreddits SET status = %s WHERE subreddit = %s"
    val = (status, subreddit)
    mycursor.execute(sql, val)
    mydb.commit()


def add_history_record(
    username=None,
    action=None,
    sql_time=None,
    address=None,
    comment_or_message=None,
    recipient_username=None,
    recipient_address=None,
    amount=None,
    hash=None,
    comment_id=None,
    notes=None,
    reddit_time=None,
    comment_text=None,
    return_status=None,
):
    if sql_time is None:
        sql_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(sql_time)

    sql = (
        "INSERT INTO history (username, action, sql_time, address, comment_or_message, recipient_username, "
        "recipient_address, amount, hash, comment_id, notes, reddit_time, comment_text, return_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    val = (
        username,
        action,
        sql_time,
        address,
        comment_or_message,
        recipient_username,
        recipient_address,
        amount,
        hash,
        comment_id,
        notes,
        reddit_time,
        comment_text,
        return_status,
    )

    mycursor.execute(sql, val)
    mydb.commit()
    return mycursor.lastrowid


def backup_keys():
    sql = "SELECT username, address, private_key FROM accounts"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    with open("../backup", "w") as f:
        for result in results:
            f.write(result[0] + "," + result[1] + "," + result[2] + "\n")


def backup_accounts():
    sql = "SELECT * FROM accounts"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    with open("../backup_accounts", "w") as f:
        for result in results:
            for r in result:
                f.write(str(r) + ";")
            f.write("\n")


def backup_history():
    sql = "SELECT * FROM history"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    with open("../backup_history", "w") as f:
        for result in results:
            for r in result:
                f.write(str(r) + ";")
            f.write("\n")


def update_percentage():
    sql = "ALTER TABLE accounts ADD percentage VARCHAR(255)"
    mycursor.execute(sql)
    sql = "UPDATE accounts SET percentage = 10"
    mycursor.execute(sql)
    mydb.commit()


def clear_messages():
    sql = "DELETE FROM messages"
    mycursor.execute(sql)
    mydb.commit()


def update_to_nano():
    sql = "UPDATE accounts SET address = REPLACE(address, 'xrb_', 'nano_')"
    mycursor.execute(sql)
    mydb.commit()


if __name__ == "__main__":
    add_subreddit("nano_tipper", True, None, "friendly")
    # init_history()
    # init_messages()
    # init_projects()
    # init_subreddits()
    # update_to_nano()
    # init_projects()
    # subreddits()
    # clear_messages()
    # add_history_record(username='zily88', sql_time='2018-04-13 09:21:28', recipient_username='nano_tipper_z_test2', action='send', hash='test', amount = 1*10**28, return_status='cleared')

    # history(100)
    # update_percentage()
    # accounts()
