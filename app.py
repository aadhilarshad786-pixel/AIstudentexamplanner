from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import database
from ml_model import analyze_study

app = Flask(__name__, static_folder="statics", static_url_path="/static")
app.secret_key = "studyai-development-secret-key"
database.init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if database.get_user(session["user_id"])["role"] != role:
                flash("This area is available for the selected account type.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = database.get_user_by_email(request.form.get("email", ""))
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session["user_id"] = user["id"]
            return redirect(url_for("parent_dashboard" if user["role"] == "parent" else "dashboard"))
        flash("The email or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        school_class = request.form.get("school_class", "10th")
        student_email = request.form.get("student_email", "").strip()
        if not full_name or not email or len(password) < 6 or password != request.form.get("confirm_password"):
            flash("Enter valid details and matching passwords (6+ characters).", "error")
        elif database.get_user_by_email(email):
            flash("An account with that email already exists.", "error")
        elif role == "parent" and (not student_email or not database.get_user_by_email(student_email)):
            flash("Enter the email used by your student account to link it.", "error")
        else:
            user_id = database.create_user(full_name, email, request.form.get("phone", ""), generate_password_hash(password), role)
            if role == "student":
                database.save_school_class(user_id, school_class)
                database.seed_school_subjects(user_id, school_class)
            if role == "parent":
                database.link_parent_student(user_id, database.get_user_by_email(student_email)["id"])
            session["user_id"] = user_id
            return redirect(url_for("parent_dashboard" if role == "parent" else "dashboard"))
    return render_template("student_signup.html")


@app.route("/parent-signup", methods=["GET", "POST"])
def parent_signup():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        student_email = request.form.get("student_email", "").strip()
        password = request.form.get("password", "")
        student = database.get_user_by_email(student_email)
        if not full_name or not email or not student_email or len(password) < 6 or password != request.form.get("confirm_password"):
            flash("Enter valid details and matching passwords (6+ characters).", "error")
        elif database.get_user_by_email(email):
            flash("An account with that email already exists.", "error")
        elif not student or student["role"] != "student":
            flash("Enter a valid student account email.", "error")
        else:
            parent_id = database.create_user(full_name, email, request.form.get("phone", ""), generate_password_hash(password), "parent")
            database.link_parent_student(parent_id, student["id"])
            session["user_id"] = parent_id
            return redirect(url_for("parent_dashboard"))
    return render_template("parent_signup.html")


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("login"))


def context(page):
    user_id = session["user_id"]
    subjects = database.get_subjects(user_id)
    metrics = database.get_metrics(user_id)
    database.seed_topics(user_id, subjects)
    return {"user": database.get_user(user_id), "subjects": subjects, "metrics": metrics,
            "study": analyze_study(subjects, metrics), "goals": database.get_goals(user_id),
            "topics": database.get_topics(user_id), "page": page}


def build_week_schedule(subjects, exam_type, week_number):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    names = [subject["name"] for subject in subjects]
    if not names:
        return []
    rotation = (week_number - 1) % len(names)
    ordered = names[rotation:] + names[:rotation]
    revision_days = {"Mid-term": 2, "Quarterly": 3, "Half-yearly": 5}.get(exam_type, 7)
    schedule = []
    for index, day in enumerate(days):
        primary = ordered[index % len(ordered)]
        secondary = ordered[(index + 1) % len(ordered)]
        sessions = [("6:00 - 7:00 PM", primary, "Learn and understand")]
        if index >= revision_days:
            sessions.append(("7:15 - 8:00 PM", primary, "Revision: close the book and recall"))
        else:
            sessions.append(("7:15 - 8:00 PM", secondary, "Practice questions"))
        sessions.append(("8:15 - 8:45 PM", "Quick revision", "Write 5 points from memory"))
        schedule.append({"day": day, "sessions": sessions})
    return schedule


@app.route("/dashboard")
@login_required
def dashboard():
    if database.get_user(session["user_id"])["role"] == "parent":
        return redirect(url_for("parent_dashboard"))
    return render_template("dashboard.html", **context("dashboard"))


@app.route("/parent/dashboard")
@role_required("parent")
def parent_dashboard():
    students = database.get_parent_students(session["user_id"])
    summaries = []
    for student in students:
        student_subjects = database.get_subjects(student["id"])
        student_metrics = database.get_metrics(student["id"])
        summaries.append({"student": student, "subjects": student_subjects, "metrics": student_metrics, "study": analyze_study(student_subjects, student_metrics), "goals": database.get_goals(student["id"])})
    return render_template("parent_dashboard.html", user=database.get_user(session["user_id"]), summaries=summaries, page="parent dashboard")


@app.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():
    if request.method == "POST":
        try:
            database.save_subjects(session["user_id"], request.form.getlist("subject_name"), request.form.getlist("mark"))
            flash("Marks saved. Your subject analysis is updated.", "success")
        except (TypeError, ValueError):
            flash("Marks must be numbers between 0 and 100.", "error")
        return redirect(url_for("subjects"))
    return render_template("subjects.html", **context("subjects"))


@app.route("/metrics", methods=["POST"])
@login_required
def metrics():
    try:
        values = [float(request.form.get(key, 0)) for key in ("study_hours", "attendance", "assignment_score", "test_score", "consistency")]
        database.save_metrics(session["user_id"], values)
        flash("Your prediction inputs were saved.", "success")
    except ValueError:
        flash("Please enter valid numeric values.", "error")
    return redirect(url_for("prediction"))


@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    user_id = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "class":
            database.save_school_class(user_id, request.form.get("school_class"))
            flash("Your school class was updated.", "success")
        elif action == "exam":
            exam_type = request.form.get("exam_type", "Quarterly")
            week = request.form.get("week", "")
            return redirect(url_for("planner", exam=exam_type, week=week))
        elif action == "reminder":
            if request.form.get("weekday") and request.form.get("start_time") and request.form.get("label", "").strip():
                database.create_reminder(user_id, request.form["weekday"], request.form["start_time"], request.form["label"].strip())
                flash("Study alarm added.", "success")
            else:
                flash("Choose a day, time and reminder name.", "error")
        return redirect(url_for("planner"))
    exam_type = request.args.get("exam", "Quarterly")
    week = request.args.get("week", type=int)
    from datetime import date
    current_week = week or date.today().isocalendar().week
    schedule = build_week_schedule(database.get_subjects(user_id), exam_type, current_week)
    return render_template("planner_mobile.html", **context("planner"), reminders=database.get_reminders(user_id), exam_type=exam_type, current_week=current_week, schedule=schedule)


@app.post("/planner/reminders/<int:reminder_id>/delete")
@login_required
def reminder_delete(reminder_id):
    database.delete_reminder(session["user_id"], reminder_id)
    return redirect(url_for("planner"))


@app.route("/prediction")
@login_required
def prediction():
    return render_template("prediction.html", **context("prediction"))


@app.route("/progress")
@login_required
def progress():
    return render_template("progress.html", **context("progress"))


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "POST":
        try:
            database.create_goal(session["user_id"], request.form["title"].strip(), float(request.form["target"]), float(request.form.get("current", 0)))
            flash("Goal added to your study plan.", "success")
        except (KeyError, ValueError):
            flash("Please enter a valid goal and scores.", "error")
        return redirect(url_for("goals"))
    return render_template("goals.html", **context("goals"))


@app.post("/topics/<int:topic_id>/toggle")
@login_required
def topic_toggle(topic_id):
    database.toggle_topic(session["user_id"], topic_id)
    return redirect(url_for("progress"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    if request.method == "POST":
        database.save_profile(user_id, request.form.get("headline", ""), request.form.get("location", ""), request.form.get("experience", "Fresher"), request.form.get("bio", ""))
        flash("Profile updated successfully.", "success")
    return render_template("profile.html", user=database.get_user(user_id), page="profile")


# ---------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
    