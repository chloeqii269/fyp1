import sqlite3

def init_db():
    conn = sqlite3.connect("Emotion_diary.db")
    c = conn.cursor()

    #user
    c.execute('''Create Table If Not Exists users 
              (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL
              )''')
    
    #emotion
    c.execute('''Create Table If Not Exists emotion_records
              (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 emotion TEXT NOT NULL,
                 confidence REAL,
                 diary_entry TEXT,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users(id)
              )''')
    
    conn.commit()
    conn.close()

if __name__ == 'main':
    init_db()
    print("Database Initialization Completed")