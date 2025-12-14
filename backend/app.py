from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import date

app = Flask(__name__)
CORS(app)

DB_NAME = "tracker.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_status (
            activity_id INTEGER,
            day TEXT,
            completed INTEGER,
            PRIMARY KEY(activity_id, day)
        )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/activities", methods=["GET"])
def get_activities():
    today = str(date.today())
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT activities.id, activities.name,
        IFNULL(daily_status.completed, 0) as completed
        FROM activities
        LEFT JOIN daily_status
        ON activities.id = daily_status.activity_id
        AND daily_status.day = ?
    """, (today,))

    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/add", methods=["POST"])
def add_activity():
    name = request.json["name"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO activities (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Activity added"})

@app.route("/toggle", methods=["POST"])
def toggle_activity():
    activity_id = request.json["id"]
    completed = request.json["completed"]
    today = str(date.today())

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO daily_status (activity_id, day, completed)
        VALUES (?, ?, ?)
    """, (activity_id, today, completed))

    conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})

@app.route("/delete", methods=["POST"])
def delete_activity():
    activity_id = request.json["id"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM activities WHERE id=?", (activity_id,))
    cur.execute("DELETE FROM daily_status WHERE activity_id=?", (activity_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
@app.route("/streak/<int:activity_id>")
def get_streak(activity_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT day, completed
        FROM daily_status
        WHERE activity_id = ?
        ORDER BY day DESC
    """, (activity_id,))

    rows = cur.fetchall()
    conn.close()

    streak = 0
    for row in rows:
        if row["completed"] == 1:
            streak += 1
        else:
            break

    return jsonify({"streak": streak})

