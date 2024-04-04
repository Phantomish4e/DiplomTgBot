import datetime
import sqlite3
import time

current_time = time.time()
table_len = 0


def create_db():
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            is_bot TEXT NOT NULL
            )
            ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Dispatchers (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, 
    username TEXT NOT NULL)''')

    # cursor.execute('DROP TABLE Incidents')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Incidents (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            description TEXT,
            sender_location TEXT NOT NULL,
            place TEXT,
            date DATETIME NOT NULL
            )
            ''')

    global table_len
    table_len = len(cursor.execute('SELECT id FROM Incidents').fetchall())

    connection.commit()
    connection.close()


def add_users_in_db(user_id, username, is_bot):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT user_id FROM Users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        print("User already exists:", existing_user)
    else:
        cursor.execute('INSERT INTO Users (user_id, username, is_bot) VALUES (?, ?, ?)',
                       (user_id, username, str(is_bot)))

    connection.commit()
    connection.close()


def see_all_users():
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()

    connection.close()
    return users


def send_msg_to_dispatcher():
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()

    connection.close()
    return users


def get_user_by_id(id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users WHERE id = ?', (id))
    user = list(cursor.fetchone())

    cursor.execute('SELECT * FROM Dispatchers WHERE user_id = ?', (user[1],))
    existing_dispatcher = cursor.fetchall()
    if existing_dispatcher:
        pass
    else:
        cursor.execute('INSERT INTO Dispatchers (user_id, username) VALUES (?, ?)',
                       (user[1], user[2]))

    connection.commit()
    connection.close()


def delete_dispatcher(id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users WHERE id = ?', (id))
    user = list(cursor.fetchone())

    cursor.execute('SELECT * FROM Dispatchers WHERE user_id = ?', (user[1],))
    existing_dispatcher = cursor.fetchall()
    if existing_dispatcher:
        cursor.execute('DELETE FROM Dispatchers WHERE user_id = ?', (user[1],))
    else:
        pass

    connection.commit()
    connection.close()


def add_incidient(type, sender_id, sender_name, sender_location, date):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute(
        'INSERT INTO Incidents (type, sender_id, sender_name, sender_location, date) VALUES (?, ?, ?, ?, ?)',
        (type, sender_id, sender_name, sender_location, date))

    connection.commit()
    connection.close()


def add_description_to_incidient(Type, sender_name, sender_location, Date, sender_id, description):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT date FROM Incidents WHERE sender_id = ?', (sender_id,))
    dates = cursor.fetchall()
    print(dates)

    cursor.execute('SELECT description FROM Incidents WHERE sender_id = ? ORDER BY id DESC LIMIT 1', (sender_id,))
    desc = cursor.fetchall()
    print(desc)
    # last_elem_desc = desc
    last_elem_desc = desc[-1]
    print(last_elem_desc)

    last_elem_desc = str(last_elem_desc)
    symbols_to_remove = "()',"

    for symbol in symbols_to_remove:
        last_elem_desc = last_elem_desc.replace(symbol, "")

    date = str(dates[-1])
    symbols_to_remove = "()',"

    for symbol in symbols_to_remove:
        date = date.replace(symbol, "")

    formated_curr_time = datetime.datetime.fromtimestamp(current_time)
    datetime_object = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")

    print(formated_curr_time)
    print(datetime_object)

    time_difference = abs((datetime_object - formated_curr_time).total_seconds())

    print(last_elem_desc)

    if time_difference <= 300 and last_elem_desc == "None":
        cursor.execute('UPDATE Incidents SET description = ? WHERE ROWID = (SELECT ROWID FROM Incidents WHERE '
                       'sender_id = ? ORDER BY date DESC LIMIT 1)', (description, sender_id))
    else:
        cursor.execute('INSERT INTO Incidents '
                       '(type, sender_id, sender_name, description, sender_location, date)'
                       ' VALUES (?, ?, ?, ?, ?, ?)',
                       (Type, sender_id, sender_name, description, sender_location, Date))

    connection.commit()
    connection.close()


def add_street_to_incident(Type, sender_name, sender_location, Date, sender_id, place, description):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT date FROM Incidents WHERE sender_id = ?', (sender_id,))
    dates = cursor.fetchall()
    print(dates)

    cursor.execute('SELECT place FROM Incidents WHERE sender_id = ? ORDER BY id DESC LIMIT 1', (sender_id,))
    desc = cursor.fetchall()
    print(desc)
    # last_elem_desc = desc
    last_elem_desc = desc[-1]
    print(last_elem_desc)

    last_elem_desc = str(last_elem_desc)
    symbols_to_remove = "()',"

    for symbol in symbols_to_remove:
        last_elem_desc = last_elem_desc.replace(symbol, "")

    date = str(dates[-1])
    symbols_to_remove = "()',"

    for symbol in symbols_to_remove:
        date = date.replace(symbol, "")

    formated_curr_time = datetime.datetime.fromtimestamp(current_time)
    datetime_object = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")

    print(formated_curr_time)
    print(datetime_object)

    time_difference = abs((datetime_object - formated_curr_time).total_seconds())

    print(last_elem_desc)

    if time_difference <= 300 and last_elem_desc == "None":
        cursor.execute('UPDATE Incidents SET place = ? WHERE ROWID = (SELECT ROWID FROM Incidents WHERE '
                       'sender_id = ? ORDER BY date DESC LIMIT 1)', (place, sender_id))
    else:
        cursor.execute('INSERT INTO Incidents '
                       '(type, sender_id, sender_name, description, sender_location, date, place)'
                       ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (Type, sender_id, sender_name, description, sender_location, Date, place))

    connection.commit()
    connection.close()


def check_for_updates():
    global table_len
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()

    temp_len = len(cursor.execute('SELECT id FROM Incidents').fetchall())
    if temp_len > table_len:
        new_value = cursor.execute('SELECT * FROM Incidents WHERE id > ?', (table_len,)).fetchall()
        table_len = temp_len
    connection.close()

    return new_value
