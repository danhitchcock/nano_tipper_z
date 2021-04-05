import time
from datetime import datetime
from shared import DATABASE_NAME, MYDB, MYCURSOR, PROGRAM_MINIMUM


def init_db():
    MYCURSOR.execute("CREATE DATABASE %s" % DATABASE_NAME)
    MYDB.commit()


def init_history():
    MYCURSOR.execute(
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
        "return_status VARCHAR(255), "
        "subreddit VARCHAR(255)"
        ")"
    )
    MYDB.commit()


def init_returns():
    MYCURSOR.execute(
        "CREATE TABLE returns ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "username VARCHAR(255), "
        "reddit_time TIMESTAMP, "
        "sql_time TIMESTAMP, "
        "recipient_username VARCHAR(255), "
        "recipient_address VARCHAR(255), "
        "amount VARCHAR(255), "
        "hash VARCHAR(255), "
        "comment_id VARCHAR(255), "
        "return_status VARCHAR(255), "
        "history_id INT"
        ")"
    )
    MYDB.commit()


def init_messages():
    MYCURSOR.execute(
        "CREATE TABLE messages ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "username VARCHAR(255), "
        "subject VARCHAR(255), "
        "message VARCHAR(5000), "
        "message_id VARCHAR(5000)"
        ")"
    )
    MYDB.commit()


def init_accounts():
    MYCURSOR.execute(
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
        "percentage VARCHAR(255), "
        "opt_in BOOL"
        ")"
    )
    MYDB.commit()


def init_subreddits():
    MYCURSOR.execute(
        "CREATE TABLE subreddits ("
        "subreddit VARCHAR(255) PRIMARY KEY, "
        "reply_to_comments BOOL, "
        "footer VARCHAR(255), "
        "status VARCHAR(255), "
        "minimum VARCHAR(255)"
        ")"
    )
    MYDB.commit()


def init_projects():
    MYCURSOR.execute(
        "CREATE TABLE projects ("
        "project VARCHAR(255) PRIMARY KEY, "
        "address VARCHAR(255)"
        ")"
    )
    MYDB.commit()


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
    subreddit=None,
):
    if sql_time is None:
        sql_time = time.strftime("%Y-%m-%d %H:%M:%S")

    sql = (
        "INSERT INTO history (username, action, sql_time, address, comment_or_message, recipient_username, "
        "recipient_address, amount, hash, comment_id, notes, reddit_time, comment_text, return_status, subreddit) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
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
        None,
        subreddit,
    )
    # todo make sure the row id is atomic
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    return MYCURSOR.lastrowid


def add_return_record(
    username=None,
    reddit_time=None,
    sql_time=None,
    recipient_username=None,
    recipient_address=None,
    amount=None,
    hash=None,
    comment_id=None,
    return_status=None,
    history_id=None,
):
    if sql_time is None:
        sql_time = time.strftime("%Y-%m-%d %H:%M:%S")

    sql = (
        "INSERT INTO returns (username, reddit_time, sql_time, recipient_username,"
        " recipient_address, amount, hash, comment_id, return_status, history_id)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    val = (
        username,
        reddit_time,
        sql_time,
        recipient_username,
        recipient_address,
        amount,
        hash,
        comment_id,
        return_status,
        history_id,
    )

    MYCURSOR.execute(sql, val)
    MYDB.commit()
    return MYCURSOR.lastrowid


def history(num_records, username=None):
    MYCURSOR.execute("SHOW COLUMNS FROM history")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)
    if username:
        MYCURSOR.execute(
            "SELECT * FROM history WHERE username = '%s' ORDER BY id DESC limit %s"
            % (username, num_records)
        )
    else:
        MYCURSOR.execute(
            "SELECT * FROM history ORDER BY id DESC limit %s" % num_records
        )
    myresult = MYCURSOR.fetchall()
    for result in reversed(myresult):
        print(result)


def messages():
    MYCURSOR.execute("SHOW COLUMNS FROM messages")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)

    MYCURSOR.execute("SELECT * FROM messages")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)


def accounts():
    MYCURSOR.execute("SHOW COLUMNS FROM accounts")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)

    MYCURSOR.execute("SELECT * FROM accounts")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)


def list_subreddits():
    MYCURSOR.execute("SELECT subreddit, status, minimum FROM subreddits")
    myresult = MYCURSOR.fetchall()
    MYDB.commit()
    return myresult


def list_returns(status=None):
    if status:
        MYCURSOR.execute("SELECT * FROM returns WHERE return_status=%s", (status,))
    else:
        MYCURSOR.execute("SELECT * FROM returns")
    myresult = MYCURSOR.fetchall()
    MYDB.commit()
    for res in myresult:
        print(res)
    return myresult


def subreddits():
    MYCURSOR.execute("SHOW COLUMNS FROM subreddits")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)

    MYCURSOR.execute("SELECT * FROM subreddits")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)


def list_columns():
    MYCURSOR.execute("SHOW COLUMNS FROM history")
    myresult = MYCURSOR.fetchall()
    for result in myresult:
        print(result)
    print("*****")
    MYCURSOR.execute("SHOW COLUMNS FROM accounts")
    myresult = MYCURSOR.fetchall()
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
    MYCURSOR.execute(sql, val)
    myresults = MYCURSOR.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        print(myresults[-5][0], datetime.fromtimestamp(time.time()))
        print((datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds())
        return (
            datetime.fromtimestamp(time.time()) - myresults[-5][0]
        ).total_seconds() > seconds


def add_subreddit(
    subreddit,
    reply_to_comments=True,
    footer="",
    status="friendly",
    minimum=PROGRAM_MINIMUM,
):
    sql = "INSERT INTO subreddits (subreddit, reply_to_comments, footer, status, minimum) VALUES (%s, %s, %s, %s, %s)"
    val = (subreddit, reply_to_comments, footer, status, minimum)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def modify_subreddit(subreddit, status):
    sql = "UPDATE subreddits SET status = %s WHERE subreddit = %s"
    val = (status, subreddit)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def rm_subreddit(subreddit):
    sql = "DELETE FROM subreddits WHERE subreddit = %s"
    val = (subreddit,)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def backup_keys():
    sql = "SELECT username, address, private_key FROM accounts"
    MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    with open("../backup", "w") as f:
        for result in results:
            f.write(result[0] + "," + result[1] + "," + result[2] + "\n")


def backup_accounts():
    sql = "SELECT * FROM accounts"
    MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    with open("../backup_accounts", "w") as f:
        for result in results:
            for r in result:
                f.write(str(r) + ";")
            f.write("\n")


def backup_history():
    sql = "SELECT * FROM history"
    MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    with open("../backup_history", "w") as f:
        for result in results:
            for r in result:
                f.write(str(r) + ";")
            f.write("\n")


def update_percentage():
    sql = "ALTER TABLE accounts ADD percentage VARCHAR(255)"
    MYCURSOR.execute(sql)
    sql = "UPDATE accounts SET percentage = 10"
    MYCURSOR.execute(sql)
    MYDB.commit()


def clear_messages():
    sql = "DELETE FROM messages"
    MYCURSOR.execute(sql)
    MYDB.commit()


def list_messages():
    MYCURSOR.execute("SELECT * FROM messages")
    myresult = MYCURSOR.fetchall()
    MYDB.commit()
    for res in myresult:
        print(res)
    return myresult


def update_to_nano():
    sql = "UPDATE accounts SET address = REPLACE(address, 'xrb_', 'nano_')"
    MYCURSOR.execute(sql)
    MYDB.commit()


def migrate_opt_out():
    sql = "ALTER TABLE accounts ADD opt_in BOOL"
    MYCURSOR.execute(sql)
    sql = "UPDATE accounts SET opt_in = TRUE"
    MYCURSOR.execute(sql)
    MYDB.commit()


def migrate_subreddit_17():
    sql = "ALTER TABLE subreddits ADD minimum VARCHAR(255)"
    MYCURSOR.execute(sql)
    sql = "UPDATE subreddits SET minimum = 0.001"
    MYCURSOR.execute(sql)
    MYDB.commit()


def migrate_add_subreddit_18():
    sql = "ALTER TABLE history ADD subreddit VARCHAR(255)"
    MYCURSOR.execute(sql)
    init_returns()
    MYDB.commit()


def migrate_reply_19():
    sql = "ALTER TABLE messages ADD message_id VARCHAR(255)"
    MYCURSOR.execute(sql)
    MYDB.commit()


if __name__ == "__main__":
    # add_subreddit("nano_tipper", True, None, "friendly")
    # init_history()
    # init_messages()
    # init_projects()
    # init_subreddits()
    # update_to_nano()
    # init_projects()
    # subreddits()
    # clear_messages()
    sql = "DELETE FROM returns"
    # val = (txn[0],)
    MYCURSOR.execute(sql)
    MYDB.commit()

    # add_return_record(
    #     username="zily88",
    #     sql_time="2021-04-03 00:00:00",
    #     recipient_username="zily88",
    #     return_status="returnable",
    #     amount=1 * 10 ** 28,
    # )
    # history(100)
    # update_percentage()
    # accounts()
