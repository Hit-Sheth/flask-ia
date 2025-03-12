from flask import Flask, request, render_template, url_for , redirect 
import sqlite3
import uuid
import random
app = Flask(__name__)
DATABASE = "ia.db"
test_id = None

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    return conn
# hi    
@app.route("/", methods=["GET", "POST"])
def index():
    global test_id
    questions = []
    selected_questions = []
    subject = request.form.get("Subject", "").upper()
    difficulty = request.form.get("difficulty", "")
    test_name = request.form.get("test_name", "")

    if test_id is None and request.method == "POST":
        test_id = str(uuid.uuid4())  
        conn = get_db_connection()
        conn.execute("INSERT INTO tests (test_id, subject, test_name) VALUES (?, ?, ?)", 
                     (test_id, subject, test_name))
        conn.commit()
        conn.close()

    if request.method == "POST":
        if "fetch_questions" in request.form:
           
            conn = get_db_connection()
            questions = conn.execute(
                "SELECT qid, question FROM questions WHERE difficulty = ? AND subject = ?",
                (difficulty, subject)).fetchall()
            conn.close()

        elif "save_questions" in request.form:
            
            selected_questions = request.form.getlist("selected_questions")

            conn = get_db_connection()
            for qid in selected_questions:
                answer = conn.execute("SELECT ANS FROM questions WHERE qid = ?", (qid,)).fetchone()["ANS"]
                conn.execute("INSERT INTO test_questions (test_id, qid, answer) VALUES (?, ?, ?)", (test_id, qid ,answer))
            conn.commit()
            conn.close()

        elif "link" in request.form:
           
            test_link = url_for('give_ia', test_id=test_id, _external=True)
            test_id = None 
            return f"Share this link with students: <a href='{test_link}'>{test_link}</a>"

    return render_template("index.html", questions=questions, subject=subject, difficulty=difficulty, test_name=test_name, test_id=test_id)

@app.route("/give_ia/<test_id>", methods=["GET", "POST"])
def give_ia(test_id):
    if request.method == "POST":
        name = request.form.get("student_name", "")
        roll = request.form.get("student_roll", "")
        if not name or not roll:
            return "Name and Roll are required fields.", 400
        conn = get_db_connection()
        conn.execute("INSERT INTO exam_taker (name, roll, test_id) VALUES (?, ?, ?)", (name, roll, test_id))
        conn.commit()
        conn.close()
        student_taste = url_for('start_ia', test_id=test_id, roll=roll, _external=True)
        return redirect(student_taste)
    return render_template("give_ia.html", test_id=test_id, name="", roll="")


s = {}  

@app.route("/start_ia/<test_id>/<roll>", methods=["GET", "POST"])
def start_ia(test_id, roll):
    global s
    conn = get_db_connection()

   
    questions = []


    if test_id not in s.keys():
        
        test_questions = conn.execute("SELECT qid FROM test_questions WHERE test_id = ?", (test_id,)).fetchall()
        for qid in test_questions:
            question = conn.execute(
                "SELECT qid, question, option_A, option_B, option_C, option_D FROM questions WHERE qid = ?",
                (qid["qid"],)
            ).fetchone()
            if question:
                questions.append(dict(question))  
        random.shuffle(questions)
        s[test_id] = questions 
    else:
        questions = s[test_id]  

    if request.method == "POST":
        if "submit" in request.form:
            for question in questions:
                answer = request.form.get(f"answer_{question['qid']}")
                if answer: 
                    conn.execute(
                        "INSERT INTO test_response (roll, qid, answer , test_id) VALUES (?, ?, ?,? )",
                        (roll, question['qid'], answer, test_id)
                    )
                else:
                    conn.execute(
                        "INSERT INTO test_response (roll, qid, answer, test_id) VALUES (?, ?, ?, ?)",
                        (roll, question['qid'], None ,test_id)
                    )
            conn.commit()
            conn.close()
            del s[test_id]  
            return "Test submitted successfully!"

    return render_template("start_ia.html", questions=questions, test_id=test_id, roll=roll)



@app.route("/show_tests", methods=["GET", "POST"])
def show_tests():
    if request.method == "POST":
        if "List the Tests" in request.form:
            subject = request.form.get("Subject", "").upper()
            conn = get_db_connection()
            tests = conn.execute('''SELECT t.test_id, t.test_name, COUNT(*) AS out_of
                                FROM tests t
                                JOIN test_questions tq ON t.test_id = tq.test_id
                                WHERE t.subject = ?
                                GROUP BY t.test_id, t.test_name''', (subject,)).fetchall()
            conn.close()
            return render_template("show_tests.html", tests=tests)

        if "Show Result" in request.form:
            test_id = request.form.get("Test")
            if test_id:  
                return redirect(url_for("show_result", test_id=test_id))

    return render_template("show_tests.html")




@app.route("/show_result/<test_id>", methods=["GET", "POST"])
def show_result(test_id):
    if request.method == "GET":
        conn = get_db_connection()
        test_name = conn.execute("SELECT test_name FROM tests WHERE test_id = ?", (test_id,)).fetchone()["test_name"]
        roll = conn.execute("select roll from exam_taker where test_id = ?", (test_id,)).fetchall()
        outof = conn.execute("select count(qid) from test_questions where test_id = ?", (test_id,)).fetchone()
        for r in roll:
            markes = 0
            qids = conn.execute("select qid from test_questions where test_id = ?", (test_id,)).fetchall()
            for qid in qids:
                answer = conn.execute("select answer from test_questions where test_id = ? and qid = ?", (test_id, qid["qid"])).fetchone()["answer"]
                response_row = conn.execute("select answer from test_response where roll = ? and qid = ? and test_id = ?", (r["roll"], qid["qid"] ,test_id)).fetchone()
                response = response_row["answer"] if response_row else None
                if response == answer:
                    markes += 1
            conn.execute("update exam_taker set markes = ? where roll = ? and test_id = ?", (markes, r["roll"] , test_id))
            conn.commit()  
        result = conn.execute("select name, roll, markes from exam_taker where test_id = ?", (test_id,)).fetchall()  
        conn.close()
        return render_template("show_result.html", test_name=test_name, test_id=test_id, result=result , outof=outof[0])
    return render_template("show_result.html", test_id=test_id)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)