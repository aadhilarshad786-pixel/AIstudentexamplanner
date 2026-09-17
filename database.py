import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "careermate.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                headline TEXT DEFAULT '',
                location TEXT DEFAULT '',
                experience TEXT DEFAULT 'Fresher',
                bio TEXT DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS skill_profiles (
                user_id INTEGER PRIMARY KEY,
                skills TEXT NOT NULL DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, mark REAL NOT NULL CHECK(mark >= 0 AND mark <= 100), UNIQUE(user_id, name), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS study_metrics (user_id INTEGER PRIMARY KEY, study_hours REAL DEFAULT 0, attendance REAL DEFAULT 0, assignment_score REAL DEFAULT 0, test_score REAL DEFAULT 0, consistency REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, target REAL NOT NULL, current REAL NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS study_topics (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, subject TEXT NOT NULL, topic TEXT NOT NULL, completed INTEGER DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS parent_students (parent_id INTEGER NOT NULL, student_id INTEGER NOT NULL, UNIQUE(parent_id, student_id), FOREIGN KEY(parent_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS syllabus_courses (id INTEGER PRIMARY KEY AUTOINCREMENT, regulation TEXT NOT NULL, department TEXT NOT NULL, semester INTEGER NOT NULL, code TEXT NOT NULL, title TEXT NOT NULL, UNIQUE(regulation, department, semester, code));
            CREATE TABLE IF NOT EXISTS syllabus_units (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, unit_no INTEGER NOT NULL, topic TEXT NOT NULL, FOREIGN KEY(course_id) REFERENCES syllabus_courses(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS previous_papers (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, year INTEGER NOT NULL, exam TEXT NOT NULL, link TEXT NOT NULL, FOREIGN KEY(course_id) REFERENCES syllabus_courses(id) ON DELETE CASCADE);
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        if "school_class" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN school_class TEXT NOT NULL DEFAULT '10th'")
        connection.execute("""CREATE TABLE IF NOT EXISTS study_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            weekday TEXT NOT NULL, start_time TEXT NOT NULL, label TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        seed_syllabus(connection)
        connection.execute("INSERT OR IGNORE INTO study_metrics (user_id) SELECT id FROM users")


def seed_syllabus(connection):
    courses = [
        ("2021", "CSE", 3, "CS3301", "Data Structures"),
        ("2021", "CSE", 3, "CS3351", "Digital Principles and Computer Organization"),
        ("2021", "CSE", 3, "CS3391", "Object Oriented Programming"),
        ("2017", "CSE", 3, "CS8391", "Data Structures"),
        ("2017", "CSE", 3, "CS8392", "Object Oriented Programming"),
            ("2024", "CSE", 3, "CS2401", "Data Structures"),
            ("2024", "CSE", 3, "CS2402", "Object Oriented Programming"),
            ("2024", "CSE", 3, "CS2403", "Database Management Systems"),
            ("2025", "CSE", 3, "CS2501", "Data Structures"),
            ("2025", "CSE", 3, "CS2502", "Object Oriented Programming"),
            ("2025", "CSE", 3, "CS2503", "Database Management Systems"),
            ("2026", "CSE", 3, "CS2601", "Data Structures"),
            ("2026", "CSE", 3, "CS2602", "Object Oriented Programming"),
            ("2026", "CSE", 3, "CS2603", "Database Management Systems"),
    ]
    for course in courses:
        connection.execute("INSERT OR IGNORE INTO syllabus_courses (regulation, department, semester, code, title) VALUES (?, ?, ?, ?, ?)", course)
    topics = {
        "CS3301": ["Arrays, stacks and queues", "Trees and binary search trees", "Graphs and graph algorithms", "Sorting and hashing", "Complexity analysis"],
        "CS3351": ["Number systems and Boolean algebra", "Combinational circuits", "Sequential circuits", "Memory and I/O organization", "Processor architecture"],
        "CS3391": ["Classes, objects and constructors", "Inheritance and polymorphism", "Exception handling", "Collections and generics", "File handling and threads"],
        "CS8391": ["Abstract data types", "Trees and heaps", "Graphs", "Sorting techniques", "Hashing"],
        "CS8392": ["Object-oriented principles", "Inheritance", "Interfaces and packages", "Exceptions", "Multithreading"],
            "CS2401": ["Introduction to Data Structures", "Arrays", "Linked Lists", "Stacks", "Queues"],
            "CS2402": ["Introduction to OOP", "Classes and Objects", "Inheritance", "Polymorphism", "Interfaces"],
            "CS2403": ["Database Concepts", "SQL Basics", "Normalization", "Transactions", "Indexing"],
            "CS2501": ["Advanced Data Structures", "Trees", "Graphs", "Hash Tables", "Complexity Analysis"],
            "CS2502": ["Advanced OOP", "Design Patterns", "UML", "Exception Handling", "Multithreading"],
            "CS2503": ["Advanced Database Management", "SQL Queries", "Database Design", "Stored Procedures", "Triggers"],
            "CS2601": ["Data Structures Review", "Algorithm Analysis", "Graph Algorithms", "Dynamic Programming", "Greedy Algorithms"],
            "CS2602": ["OOP Review", "Design Patterns", "Software Development Life Cycle", "Testing", "Documentation"],
            "CS2603": ["Database Management Systems Review", "NoSQL Databases", "Data Warehousing", "Big Data", "Data Mining"],
    }
    for code, unit_topics in topics.items():
        row = connection.execute("SELECT id FROM syllabus_courses WHERE code = ? LIMIT 1", (code,)).fetchone()
        for unit_no, topic in enumerate(unit_topics, 1):
            connection.execute("INSERT OR IGNORE INTO syllabus_units (course_id, unit_no, topic) VALUES (?, ?, ?)", (row["id"], unit_no, topic))
        for year in (2023, 2024, 2025):
            connection.execute("INSERT OR IGNORE INTO previous_papers (course_id, year, exam, link) VALUES (?, ?, ?, ?)", (row["id"], year, "End Semester Examination", "https://www.annauniv.edu/"))


def create_user(full_name, email, phone, password_hash, role="student"):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO users (full_name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (full_name, email.lower().strip(), phone, password_hash, role),
        )
        user_id = cursor.lastrowid
        connection.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
        connection.execute("INSERT INTO skill_profiles (user_id) VALUES (?)", (user_id,))
        connection.execute("INSERT INTO study_metrics (user_id) VALUES (?)", (user_id,))
        return user_id


def seed_school_subjects(user_id, school_class):
    subjects = {
        "10th": ["Tamil", "English", "Mathematics", "Science", "Social Science"],
        "12th": ["Tamil", "English", "Mathematics", "Physics", "Chemistry", "Computer Science"],
    }.get(school_class, [])
    with get_connection() as connection:
        for name in subjects:
            connection.execute("INSERT OR IGNORE INTO subjects (user_id, name, mark) VALUES (?, ?, 0)", (user_id, name))


def get_user_by_email(email):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()


def get_user(user_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT users.*, profiles.headline, profiles.location, profiles.experience, profiles.bio "
            "FROM users LEFT JOIN profiles ON profiles.user_id = users.id WHERE users.id = ?",
            (user_id,),
        ).fetchone()


def save_school_class(user_id, school_class):
    if school_class not in ("10th", "12th"):
        return
    with get_connection() as connection:
        connection.execute("UPDATE users SET school_class = ? WHERE id = ?", (school_class, user_id))


def get_reminders(user_id):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM study_reminders WHERE user_id = ? ORDER BY weekday, start_time", (user_id,)).fetchall()


def create_reminder(user_id, weekday, start_time, label):
    with get_connection() as connection:
        connection.execute("INSERT INTO study_reminders (user_id, weekday, start_time, label) VALUES (?, ?, ?, ?)", (user_id, weekday, start_time, label))


def delete_reminder(user_id, reminder_id):
    with get_connection() as connection:
        connection.execute("DELETE FROM study_reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))


def link_parent_student(parent_id, student_id):
    with get_connection() as connection:
        connection.execute("INSERT OR IGNORE INTO parent_students (parent_id, student_id) VALUES (?, ?)", (parent_id, student_id))


def get_parent_students(parent_id):
    with get_connection() as connection:
        return connection.execute("SELECT users.* FROM users JOIN parent_students ON parent_students.student_id = users.id WHERE parent_students.parent_id = ?", (parent_id,)).fetchall()


def get_syllabus_courses(regulation="2021", department="CSE", semester=3):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM syllabus_courses WHERE regulation = ? AND department = ? AND semester = ? ORDER BY code", (regulation, department, semester)).fetchall()


def get_syllabus_course(course_id):
    with get_connection() as connection:
        course = connection.execute("SELECT * FROM syllabus_courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            return None, [], []
        units = connection.execute("SELECT * FROM syllabus_units WHERE course_id = ? ORDER BY unit_no", (course_id,)).fetchall()
        papers = connection.execute("SELECT * FROM previous_papers WHERE course_id = ? ORDER BY year DESC", (course_id,)).fetchall()
        return course, units, papers


def save_profile(user_id, headline, location, experience, bio):
    with get_connection() as connection:
        connection.execute(
            "UPDATE profiles SET headline = ?, location = ?, experience = ?, bio = ? WHERE user_id = ?",
            (headline, location, experience, bio, user_id),
        )


def get_skills(user_id):
    with get_connection() as connection:
        row = connection.execute("SELECT skills FROM skill_profiles WHERE user_id = ?", (user_id,)).fetchone()
        return row["skills"] if row else ""


def save_skills(user_id, skills):
    with get_connection() as connection:
        connection.execute(
            "UPDATE skill_profiles SET skills = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (skills, user_id),
        )


def get_subjects(user_id):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM subjects WHERE user_id = ? ORDER BY mark ASC, name", (user_id,)).fetchall()


def save_subjects(user_id, names, marks):
    with get_connection() as connection:
        connection.execute("DELETE FROM subjects WHERE user_id = ?", (user_id,))
        for name, mark in zip(names, marks):
            name = name.strip()
            if name:
                connection.execute("INSERT INTO subjects (user_id, name, mark) VALUES (?, ?, ?)", (user_id, name, max(0, min(100, float(mark)))))


def get_metrics(user_id):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM study_metrics WHERE user_id = ?", (user_id,)).fetchone()


def save_metrics(user_id, values):
    with get_connection() as connection:
        connection.execute("UPDATE study_metrics SET study_hours = ?, attendance = ?, assignment_score = ?, test_score = ?, consistency = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (*values, user_id))


def get_goals(user_id):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM goals WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()


def create_goal(user_id, title, target, current):
    with get_connection() as connection:
        connection.execute("INSERT INTO goals (user_id, title, target, current) VALUES (?, ?, ?, ?)", (user_id, title, target, current))


def get_topics(user_id):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM study_topics WHERE user_id = ? ORDER BY completed, subject", (user_id,)).fetchall()


def seed_topics(user_id, subjects):
    with get_connection() as connection:
        if connection.execute("SELECT COUNT(*) FROM study_topics WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
            for subject in subjects:
                connection.execute("INSERT INTO study_topics (user_id, subject, topic) VALUES (?, ?, ?)", (user_id, subject["name"], f"Core {subject['name']} concepts"))


def toggle_topic(user_id, topic_id):
    with get_connection() as connection:
        connection.execute("UPDATE study_topics SET completed = CASE completed WHEN 1 THEN 0 ELSE 1 END WHERE id = ? AND user_id = ?", (topic_id, user_id))