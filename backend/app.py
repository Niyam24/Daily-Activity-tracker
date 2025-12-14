from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import date
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# ---------------- DATABASE CONNECTION ----------------

def get_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    )

# ---------------- INITIALIZE TABLES ----------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_status (
            activity_id INTEGER,
            day DATE,
            completed INTEGER,
            PRIMARY KEY (activity_id, day),
            FOREIGN KEY (activity_id) REFERENCES activities(id)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------------- ROUTES ----------------

@app.route("/activities", methods=["GET"])
def get_activities():
    today = date.today()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id, a.name, COALESCE(d.completed, 0)
        FROM activities a
        LEFT JOIN daily_status d
        ON a.id = d.activity_id AND d.day = %s
        ORDER BY a.id;
    """, (today,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "name": r[1],
            "completed": r[2]
        }
        for r in rows
    ])


@app.route("/add", methods=["POST"])
def add_activity():
    name = request.json["name"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO activities (name) VALUES (%s);",
        (name,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Activity added"})


@app.route("/toggle", methods=["POST"])
def toggle_activity():
    activity_id = request.json["id"]
    completed = request.json["completed"]
    today = date.today()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO daily_status (activity_id, day, completed)
        VALUES (%s, %s, %s)
        ON CONFLICT (activity_id, day)
        DO UPDATE SET completed = EXCLUDED.completed;
    """, (activity_id, today, completed))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Updated"})


@app.route("/delete", methods=["POST"])
def delete_activity():
    activity_id = request.json["id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM daily_status WHERE activity_id = %s;",
        (activity_id,)
    )
    cur.execute(
        "DELETE FROM activities WHERE id = %s;",
        (activity_id,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Deleted"})


# ---------------- STREAK ROUTE ----------------

@app.route("/streak/<int:activity_id>")
def get_streak(activity_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT day, completed
        FROM daily_status
        WHERE activity_id = %s
        ORDER BY day DESC;
    """, (activity_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    streak = 0
    for r in rows:
        if r[1] == 1:
            streak += 1
        else:
            break

    return jsonify({"streak": streak})


# ---------------- RUN APP (RENDER FIX) ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
