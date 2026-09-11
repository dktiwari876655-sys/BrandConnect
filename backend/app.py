from flask import Flask, session, render_template, request, redirect, url_for, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pathlib import Path
import os
import razorpay
from dotenv import load_dotenv
from cloudinary_service import configure_cloudinary, upload_creator_image
from mongo_service import connect_mongodb, get_database, sync_creator

load_dotenv(Path(__file__).with_name(".env"))

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")


razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "brandconnect-dev-key")
DB = Path(__file__).with_name("brandconnect.db")
@app.route("/google45d6f7d4de3223e2.html")
def google_verification():
    return send_file(Path(__file__).with_name("google45d6f7d4de3223e2.html"))

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS creators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        platform TEXT NOT NULL,
        category TEXT NOT NULL,
        followers INTEGER NOT NULL,
        avg_views INTEGER NOT NULL,
        price INTEGER NOT NULL,
        location TEXT NOT NULL,
        bio TEXT DEFAULT '',
        image_url TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_name TEXT NOT NULL,
        category TEXT NOT NULL,
        budget INTEGER NOT NULL,
        platform TEXT NOT NULL,
        location TEXT DEFAULT '',
        description TEXT DEFAULT '',
        user_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        creator_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS collaboration_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        brand_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        deal_status TEXT DEFAULT 'accepted',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
                CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        brand_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        upi_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        
       );
    """)

    try:
        conn.execute(
            "ALTER TABLE creators ADD COLUMN image_url TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass

    try:
         
     conn.execute(
            "ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    # Existing database me agar columns missing hain
    try:
        conn.execute(
            "ALTER TABLE campaigns ADD COLUMN user_id INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN creator_id INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE collaboration_requests ADD COLUMN deal_status TEXT DEFAULT 'accepted'"
        )
    except sqlite3.OperationalError:
        pass

    # Default creators
    count = conn.execute(
        "SELECT COUNT(*) FROM creators"
    ).fetchone()[0]

    if count == 0:
        conn.executemany("""
            INSERT INTO creators
            (name, platform, category, followers, avg_views, price, location, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                "Tech With Aman",
                "YouTube",
                "Technology",
                8500,
                4200,
                1200,
                "Jaipur",
                "Tech reviews and useful apps."
            ),
            (
                "Foodie Riya",
                "YouTube",
                "Food",
                15000,
                7200,
                1800,
                "Delhi",
                "Food and local restaurant content."
            ),
            (
                "Gaming Raj",
                "YouTube",
                "Gaming",
                28000,
                12500,
                3000,
                "Rajasthan",
                "Gaming and esports creator."
            ),
            (
                "Style With Neha",
                "Instagram",
                "Fashion",
                12000,
                6100,
                1500,
                "Jaipur",
                "Fashion, beauty and lifestyle."
            )
        ])

    conn.commit()
    if get_database() is not None:
        for creator in conn.execute("SELECT * FROM creators").fetchall():
            sync_creator(creator)
    conn.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        conn = db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            if user["role"] == "brand":
                return redirect(url_for("brand_dashboard"))
            else:
                return redirect(url_for("creator_dashboard"))

        return "Invalid email or password", 401

    return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        role = request.form["role"]

        creator_id = request.form.get("creator_id") or None

        conn = db()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            return "Email already registered", 400

        if role == "creator" and creator_id:
            creator = conn.execute(
                "SELECT * FROM creators WHERE id = ?",
                (creator_id,)
            ).fetchone()

            if not creator:
                conn.close()
                return "Creator profile not found", 404

        if role != "creator":
            creator_id = None

        conn.execute("""
            INSERT INTO users
            (name, email, password, role, creator_id) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            email,
            password,
            role,
            creator_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")
@app.route("/brand-dashboard")
def brand_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    campaigns = conn.execute(
        "SELECT * FROM campaigns WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    collaboration_requests = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.status,
            collaboration_requests.deal_status,
            collaboration_requests.created_at,
            creators.name AS creator_name,
            creators.platform,
            creators.category,
            campaigns.brand_name,
            campaigns.category AS campaign_category,
            campaigns.budget,
            campaigns.platform AS campaign_platform
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN creators
            ON collaboration_requests.creator_id = creators.id
        WHERE campaigns.user_id = ?
        ORDER BY collaboration_requests.id DESC
    """, (session["user_id"],)).fetchall()

    notifications = conn.execute("""
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    unread_messages = conn.execute("""
        SELECT COUNT(*) AS count
        FROM messages
        WHERE receiver_id = ?
          AND is_read = 0
    """, (session["user_id"],)).fetchone()["count"]

    unread_request = conn.execute("""
        SELECT collaboration_requests.id AS request_id
        FROM messages
        JOIN users
            ON messages.sender_id = users.id
        JOIN collaboration_requests
            ON collaboration_requests.creator_id = users.creator_id
        WHERE messages.receiver_id = ?
          AND messages.is_read = 0
        ORDER BY messages.id DESC
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    unread_request_id = unread_request["request_id"] if unread_request else None
    total_requests = conn.execute("""
        SELECT COUNT(*) AS count
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE campaigns.user_id = ?
    """, (session["user_id"],)).fetchone()["count"]

    accepted_requests = conn.execute("""
        SELECT COUNT(*) AS count
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
    """, (session["user_id"],)).fetchone()["count"]

    pending_requests = conn.execute("""
        SELECT COUNT(*) AS count
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE campaigns.user_id = ?
          AND collaboration_requests.status = 'pending'
    """, (session["user_id"],)).fetchone()["count"]

    rejected_requests = conn.execute("""
        SELECT COUNT(*) AS count
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE campaigns.user_id = ?
          AND collaboration_requests.status = 'rejected'
    """, (session["user_id"],)).fetchone()["count"]

    conn.close()

    return render_template(
        "brand_dashboard.html",
        user_name=session["user_name"],
        user_role=session["user_role"],
        campaigns=campaigns,
         unread_messages=unread_messages,
          unread_request_id=unread_request_id,   
        collaboration_requests=collaboration_requests,
        notifications=notifications,
        total_requests=total_requests,
        accepted_requests=accepted_requests,
        pending_requests=pending_requests,
        rejected_requests=rejected_requests
            
    )
    
@app.route("/edit-creator-profile", methods=["GET", "POST"])
def edit_creator_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "creator":
        return "Access denied", 403

    conn = db()

    creator = conn.execute(
        "SELECT * FROM creators WHERE id = (SELECT creator_id FROM users WHERE id = ?)",
        (session["user_id"],)
    ).fetchone()

    if not creator:
        conn.close()
        return "Creator profile not found", 404

    if request.method == "POST":

        name = request.form["name"].strip()
        platform = request.form["platform"].strip()
        category = request.form["category"].strip()
        followers = int(request.form["followers"])
        avg_views = int(request.form["avg_views"])
        price = int(request.form["price"])
        location = request.form["location"].strip()
        bio = request.form["bio"].strip()
        image_url = creator["image_url"] or ""

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            try:
                image_url = upload_creator_image(image_file, creator["id"])
            except RuntimeError as error:
                conn.close()
                flash(str(error), "error")
                return redirect(url_for("edit_creator_profile"))
            except Exception:
                conn.close()
                flash("Image upload failed. Please try again.", "error")
                return redirect(url_for("edit_creator_profile"))

        conn.execute("""
            UPDATE creators
            SET
                name = ?,
                platform = ?,
                category = ?,
                followers = ?,
                avg_views = ?,
                price = ?,
                location = ?,
                bio = ?,
                image_url = ?
            WHERE id = ?
        """, (
            name,
            platform,
            category,
            followers,
            avg_views,
            price,
            location,
            bio,
            image_url,
            creator["id"]
        ))

        conn.commit()
        updated_creator = conn.execute(
            "SELECT * FROM creators WHERE id = ?", (creator["id"],)
        ).fetchone()
        sync_creator(updated_creator)
        conn.close()

        return redirect(url_for("creator_dashboard"))

    conn.close()

    return render_template(
        "edit_creator_profile.html",
        creator=creator
    )
@app.route("/chat/<int:request_id>", methods=["GET", "POST"])
def chat(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = db()

    # Get deal
    deal = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.status,
            collaboration_requests.deal_status,
            campaigns.user_id AS brand_id,
            collaboration_requests.creator_id,
            creators.name AS creator_name,
            campaigns.brand_name
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN creators
            ON collaboration_requests.creator_id = creators.id
        WHERE collaboration_requests.id = ?
          AND collaboration_requests.status = 'accepted'
    """, (request_id,)).fetchone()

    if not deal:
        conn.close()
        return "Chat not found", 404

    # =========================
    # FIND RECEIVER
    # =========================

    # BRAND
    if session["user_role"] == "brand":

        if deal["brand_id"] != session["user_id"]:
            conn.close()
            return "Access denied", 403

        receiver = conn.execute("""
            SELECT id
            FROM users
            WHERE creator_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (deal["creator_id"],)).fetchone()

        if not receiver:
            conn.close()
            return "Creator account not found", 404

        receiver_id = receiver["id"]

    # CREATOR
    elif session["user_role"] == "creator":

        current_user = conn.execute("""
            SELECT creator_id
            FROM users
            WHERE id = ?
        """, (session["user_id"],)).fetchone()

        if not current_user:
            conn.close()
            return "Creator account not found", 404

        if current_user["creator_id"] != deal["creator_id"]:
            conn.close()
            return "Access denied", 403

        receiver_id = deal["brand_id"]

    else:
        conn.close()
        return "Access denied", 403

    # =========================
    # MARK MESSAGES AS READ
    # =========================

    conn.execute("""
        UPDATE messages
        SET is_read = 1
        WHERE receiver_id = ?
          AND sender_id = ?
          AND is_read = 0
    """, (
        session["user_id"],
        receiver_id
    ))

    # Mark chat notifications as read
    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
          AND message LIKE '💬 New message%'
          AND is_read = 0
    """, (session["user_id"],))

    conn.commit()

    # =========================
    # SEND MESSAGE
    # =========================

    if request.method == "POST":

        message = request.form.get("message", "").strip()

        if message:

            conn.execute("""
                INSERT INTO messages
                (sender_id, receiver_id, message, is_read)
                VALUES (?, ?, ?, 0)
            """, (
                session["user_id"],
                receiver_id,
                message
            ))

            conn.execute("""
                INSERT INTO notifications
                (user_id, message, is_read)
                VALUES (?, ?, 0)
            """, (
                receiver_id,
                f"💬 New message from {session['user_name']}"
            ))

            conn.commit()

            # Refresh chat after sending
            conn.close()

            return redirect(
                url_for("chat", request_id=request_id)
            )

    # =========================
    # LOAD CHAT MESSAGES
    # =========================

    messages = conn.execute("""
        SELECT
            messages.*,
            users.name AS sender_name
        FROM messages
        JOIN users
            ON messages.sender_id = users.id
        WHERE
            (messages.sender_id = ? AND messages.receiver_id = ?)
            OR
            (messages.sender_id = ? AND messages.receiver_id = ?)
        ORDER BY messages.id ASC
    """, (
        session["user_id"],
        receiver_id,
        receiver_id,
        session["user_id"]
    )).fetchall()

    conn.close()

    return render_template(
        "chat.html",
        deal=deal,
        messages=messages
    )
@app.route("/creator-dashboard")
def creator_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "creator":
        return "Access denied", 403

    conn = db()

    creator = conn.execute(
        """
        SELECT * FROM creators
        WHERE id = (
            SELECT creator_id
            FROM users
            WHERE id = ?
        )
        """,
        (session["user_id"],)
    ).fetchone()

    requests = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.status,
            collaboration_requests.deal_status,
            collaboration_requests.created_at,
            campaigns.brand_name,
            campaigns.category,
            campaigns.budget,
            campaigns.platform,
            campaigns.location,
            campaigns.description
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN users
            ON users.creator_id = collaboration_requests.creator_id
        WHERE users.id = ?
        ORDER BY collaboration_requests.id DESC
    """, (session["user_id"],)).fetchall()

    # 💰 LOAD PAYMENTS RECEIVED
    payments = conn.execute("""
        SELECT
            payments.id,
            payments.request_id,
            payments.amount,
            payments.upi_id,
            payments.status,
            payments.created_at,
            campaigns.brand_name
        FROM payments
        JOIN collaboration_requests
            ON payments.request_id = collaboration_requests.id
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE payments.creator_id = ?
        ORDER BY payments.id DESC
    """, (creator["id"],)).fetchall()

    # 🔔 LOAD NOTIFICATIONS
    notifications = conn.execute("""
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    unread_messages = conn.execute("""
    SELECT COUNT(*) AS count
    FROM messages
    WHERE receiver_id = ?
      AND is_read = 0
""", (session["user_id"],)).fetchone()["count"]
        # ⭐ RATING DATA
    rating_data = conn.execute("""
        SELECT
            COUNT(*) AS total_reviews,
            COALESCE(AVG(rating), 0) AS average_rating
        FROM reviews
        WHERE reviewee_id = ?
    """, (creator["id"],)).fetchone()

    # ⭐ REVIEWS
    reviews = conn.execute("""
        SELECT
            reviews.rating,
            reviews.review,
            reviews.created_at,
            users.name AS reviewer_name
        FROM reviews
        JOIN users
            ON reviews.reviewer_id = users.id
        WHERE reviews.reviewee_id = ?
        ORDER BY reviews.id DESC
    """, (creator["id"],)).fetchall()

    conn.close()

    return render_template(
        "creator_dashboard.html",
        user_name=session["user_name"],
        creator=creator,
        requests=requests,
        payments=payments,
        notifications=notifications,
        unread_messages=unread_messages,
        rating_data=rating_data,
        reviews=reviews
    )
@app.route("/creators")
def creators():
    category = request.args.get("category", "").strip()
    max_price = request.args.get("max_price", "").strip()
    query = "SELECT * FROM creators WHERE 1=1"
    params = []
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if max_price.isdigit():
        query += " AND price <= ?"
        params.append(int(max_price))
    query += " ORDER BY followers DESC"
    conn = db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return render_template("creators.html", creators=rows, category=category, max_price=max_price)

@app.route("/campaign", methods=["GET", "POST"])
def campaign():
      if "user_id" not in session:
        return redirect(url_for("login"))
      if request.method == "POST":
        brand = request.form["brand_name"].strip()
        category = request.form["category"].strip()
        budget = int(request.form["budget"])
        platform = request.form["platform"]
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        conn = db()
        conn.execute("""
    INSERT INTO campaigns
    (brand_name, category, budget, platform, location, description, user_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
        """,(brand, category, budget, platform, location, description, session["user_id"]))
        conn.commit()
        campaign_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return redirect(url_for("matches", campaign_id=campaign_id))
      return render_template("campaign.html")

@app.route("/matches/<int:campaign_id>")
def matches(campaign_id):
    conn = db()
    campaign_row = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not campaign_row:
        conn.close()
        return "Campaign not found", 404

    # Simple MVP matching: category + platform + price within budget.
    rows = conn.execute("""
        SELECT * FROM creators
        WHERE price <= ?
          AND (category LIKE ? OR ? = '')
          AND (platform = ? OR ? = 'Any')
        ORDER BY
          CASE WHEN category LIKE ? THEN 0 ELSE 1 END,
          price ASC,
          followers DESC
    """, (
        campaign_row["budget"],
        f"%{campaign_row['category']}%",
        campaign_row["category"],
        campaign_row["platform"],
        campaign_row["platform"],
        f"%{campaign_row['category']}%"
    )).fetchall()
    conn.close()
    return render_template("matches.html", campaign=campaign_row, creators=rows)

@app.route("/admin")
def admin():
    conn = db()
    creators = conn.execute("SELECT * FROM creators ORDER BY id DESC").fetchall()
    campaigns = conn.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", creators=creators, campaigns=campaigns)
@app.route("/contact-creator/<int:campaign_id>/<int:creator_id>", methods=["POST"])
def contact_creator(campaign_id, creator_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    # Check campaign belongs to logged-in brand
    campaign_row = conn.execute(
        "SELECT * FROM campaigns WHERE id=? AND user_id=?",
        (campaign_id, session["user_id"])
    ).fetchone()

    if not campaign_row:
        conn.close()
        return "Campaign not found or access denied", 404

    # Check creator exists
    creator = conn.execute(
        "SELECT * FROM creators WHERE id=?",
        (creator_id,)
    ).fetchone()

    if not creator:
        conn.close()
        return "Creator not found", 404

    # Check if request already exists
    existing_request = conn.execute("""
        SELECT id, status
        FROM collaboration_requests
        WHERE campaign_id = ?
          AND creator_id = ?
    """, (
        campaign_id,
        creator_id
    )).fetchone()

    if existing_request:
        conn.close()

        if existing_request["status"] == "accepted":
            return f"Collaboration with {creator['name']} is already accepted!"

        elif existing_request["status"] == "rejected":
            return f"Collaboration request to {creator['name']} was already rejected."

        else:
            return f"Collaboration request to {creator['name']} is already pending!"

    # Create new collaboration request
    conn.execute("""
        INSERT INTO collaboration_requests
        (campaign_id, creator_id, brand_id, status)
        VALUES (?, ?, ?, 'pending')
    """, (
        campaign_id,
        creator_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return f"Collaboration request sent to {creator['name']}!"
    return f"Collaboration request sent to {creator['name']}!"
@app.route("/creator/<int:creator_id>")
def creator_profile(creator_id):

    conn = db()

    creator = conn.execute(
        "SELECT * FROM creators WHERE id = ?",
        (creator_id,)
    ).fetchone()

    campaigns = []

    if "user_id" in session and session.get("user_role") == "brand":
        campaigns = conn.execute(
            "SELECT * FROM campaigns WHERE user_id = ? ORDER BY id DESC",
            (session["user_id"],)
        ).fetchall()

    conn.close()

    if not creator:
        return "Creator not found", 404

    return render_template(
        "creator_profile.html",
        creator=creator,
        campaigns=campaigns
    )
    
@app.route("/collaboration/<int:request_id>/accept", methods=["POST"])
def accept_collaboration(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "creator":
        return "Access denied", 403

    conn = db()

    request_row = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.brand_id,
            creators.name AS creator_name
        FROM collaboration_requests
        JOIN users
            ON users.creator_id = collaboration_requests.creator_id
        JOIN creators
            ON creators.id = collaboration_requests.creator_id
        WHERE collaboration_requests.id = ?
          AND users.id = ?
    """, (request_id, session["user_id"])).fetchone()

    if not request_row:
        conn.close()
        return "Request not found or access denied", 404

    conn.execute("""
        UPDATE collaboration_requests
        SET status = 'accepted'
        WHERE id = ?
    """, (request_id,))

    conn.execute("""
        INSERT INTO notifications (user_id, message)
        VALUES (?, ?)
    """, (
        request_row["brand_id"],
        f"{request_row['creator_name']} accepted your collaboration request."
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("creator_dashboard"))


@app.route("/collaboration/<int:request_id>/reject", methods=["POST"])
def reject_collaboration(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "creator":
        return "Access denied", 403

    conn = db()

    request_row = conn.execute("""
    SELECT
        collaboration_requests.id,
        collaboration_requests.brand_id,
        creators.name AS creator_name
    FROM collaboration_requests
    JOIN users
        ON users.creator_id = collaboration_requests.creator_id
    JOIN creators
        ON creators.id = collaboration_requests.creator_id
    WHERE collaboration_requests.id = ?
      AND users.id = ?
""", (request_id, session["user_id"])).fetchone()
    if not request_row:
        conn.close()
        return "Request not found or access denied", 404

    
    conn.execute("""
    UPDATE collaboration_requests
    SET status = 'accepted',
        deal_status = 'accepted'
    WHERE id = ?
""", (request_id,))
    conn.execute("""
        INSERT INTO notifications (user_id, message)
        VALUES (?, ?)
    """, (
        request_row["brand_id"],
        f"{request_row['creator_name']} rejected your collaboration request."
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("creator_dashboard"))
@app.route("/deal/<int:request_id>/complete", methods=["POST"])
def complete_deal(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    request_row = conn.execute("""
        SELECT collaboration_requests.id
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
          AND collaboration_requests.deal_status = 'in_progress'
    """, (request_id, session["user_id"])).fetchone()

    if not request_row:
        conn.close()
        return "Deal not found or access denied", 404

    conn.execute("""
        UPDATE collaboration_requests
        SET deal_status = 'completed'
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("brand_dashboard"))
@app.route("/pay-creator/<int:request_id>")
def pay_creator(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    deal = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.creator_id,
            collaboration_requests.status,
            collaboration_requests.deal_status,
            campaigns.user_id AS brand_id,
            campaigns.brand_name,
            creators.name AS creator_name,
            creators.price,

            EXISTS(
                SELECT 1
                FROM payments
                WHERE payments.request_id = collaboration_requests.id
                  AND payments.status = 'paid'
            ) AS already_paid

        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN creators
            ON collaboration_requests.creator_id = creators.id

        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
          AND collaboration_requests.deal_status = 'completed'

    """, (request_id, session["user_id"])).fetchone()

    conn.close()

    if not deal:
        return "Deal not found or access denied", 404

    return render_template(
        "pay_creator.html",
        deal=deal
    )


@app.route("/create-payment-order/<int:request_id>", methods=["POST"])
def create_payment_order(request_id):

    if "user_id" not in session:
        return {"error": "Please login first"}, 401

    if session["user_role"] != "brand":
        return {"error": "Access denied"}, 403

    conn = db()

    deal = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.creator_id,
            campaigns.user_id AS brand_id,
            campaigns.brand_name,
            creators.name AS creator_name,
            creators.price
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN creators
            ON collaboration_requests.creator_id = creators.id
        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
          AND collaboration_requests.deal_status = 'completed'
    """, (request_id, session["user_id"])).fetchone()

    conn.close()

    if not deal:
        return {"error": "Deal not found or access denied"}, 404

    # Prevent creating another order if already paid
    conn = db()

    existing_payment = conn.execute("""
        SELECT id
        FROM payments
        WHERE request_id = ?
          AND status = 'paid'
        LIMIT 1
    """, (request_id,)).fetchone()

    conn.close()

    if existing_payment:
        return {
            "error": "This deal has already been paid."
        }, 400

    amount = int(deal["price"])

    try:

        payment_data = {
            "amount": amount * 100,
            "currency": "INR",
            "receipt": f"brandconnect_{request_id}"
        }

        print("Creating Razorpay order:", payment_data)

        order = razorpay_client.order.create(
            data=payment_data
        )

        print("Razorpay order created:", order)

        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID
        }

    except Exception as e:

        print("========== RAZORPAY ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print("====================================")

        return {
            "error": str(e)
        }, 500


@app.route("/verify-payment", methods=["POST"])
def verify_payment():

    if "user_id" not in session:
        return {
            "success": False,
            "error": "Please login first"
        }, 401

    if session["user_role"] != "brand":
        return {
            "success": False,
            "error": "Access denied"
        }, 403

    data = request.get_json()

    request_id = data.get("request_id")
    amount = data.get("amount")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")

    if not all([
        request_id,
        amount,
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature
    ]):
        return {
            "success": False,
            "error": "Missing payment information"
        }, 400

    try:

        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

    except Exception as e:

        print("Payment verification error:", e)

        return {
            "success": False,
            "error": "Payment verification failed"
        }, 400

    conn = db()

    # Check deal
    deal = conn.execute("""
        SELECT
            collaboration_requests.creator_id,
            campaigns.user_id AS brand_id
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
          AND collaboration_requests.deal_status = 'completed'
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if not deal:
        conn.close()

        return {
            "success": False,
            "error": "Deal not found"
        }, 404

    # Prevent duplicate payment
    existing_payment = conn.execute("""
        SELECT id
        FROM payments
        WHERE request_id = ?
          AND status = 'paid'
        LIMIT 1
    """, (request_id,)).fetchone()

    if existing_payment:
        conn.close()

        return {
            "success": True,
            "message": "Payment already recorded"
        }

    # Get UPI information
    try:

        payment_info = razorpay_client.payment.fetch(
            razorpay_payment_id
        )

        upi_id = payment_info.get("vpa", "")

    except Exception:

        upi_id = ""

    # Save payment
    conn.execute("""
        INSERT INTO payments
        (request_id, brand_id, creator_id, amount, upi_id, status)
        VALUES (?, ?, ?, ?, ?, 'paid')
    """, (
        request_id,
        session["user_id"],
        deal["creator_id"],
        amount,
        upi_id
    ))

    conn.commit()
    conn.close()

    return {
        "success": True
    }
    

@app.route("/deal/<int:request_id>/start", methods=["POST"])
def start_deal(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    request_row = conn.execute("""
        SELECT collaboration_requests.id
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
    """, (request_id, session["user_id"])).fetchone()

    if not request_row:
        conn.close()
        return "Deal not found or access denied", 404

    conn.execute("""
        UPDATE collaboration_requests
        SET deal_status = 'in_progress'
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("brand_dashboard"))
@app.route("/")
def home():
    conn = db()

    creators = conn.execute("""
        SELECT * FROM creators
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template("index.html", creators=creators)

@app.route("/payments")
def payments():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = db()

    if session["user_role"] == "brand":

        payments = conn.execute("""
            SELECT
                payments.id,
                payments.amount,
                payments.upi_id,
                payments.status,
                payments.created_at,
                creators.name AS creator_name,
                campaigns.brand_name
            FROM payments
            JOIN creators
                ON payments.creator_id = creators.id
            JOIN collaboration_requests
                ON payments.request_id = collaboration_requests.id
            JOIN campaigns
                ON collaboration_requests.campaign_id = campaigns.id
            WHERE payments.brand_id = ?
            ORDER BY payments.id DESC
        """, (session["user_id"],)).fetchall()

    elif session["user_role"] == "creator":

        creator = conn.execute("""
            SELECT creator_id
            FROM users
            WHERE id = ?
        """, (session["user_id"],)).fetchone()

        payments = conn.execute("""
            SELECT
                payments.id,
                payments.amount,
                payments.upi_id,
                payments.status,
                payments.created_at,
                campaigns.brand_name
            FROM payments
            JOIN collaboration_requests
                ON payments.request_id = collaboration_requests.id
            JOIN campaigns
                ON collaboration_requests.campaign_id = campaigns.id
            WHERE payments.creator_id = ?
            ORDER BY payments.id DESC
        """, (creator["creator_id"],)).fetchall()

    else:
        conn.close()
        return "Access denied", 403

    conn.close()

    return render_template(
        "payments.html",
        payments=payments
    )
    # ⭐ LOAD CREATOR RATING & REVIEWS
    rating_data = conn.execute("""
        SELECT
            AVG(rating) AS average_rating,
            COUNT(*) AS review_count
        FROM reviews
        WHERE reviewee_id = ?
    """, (creator["id"],)).fetchone()

    reviews = conn.execute("""
        SELECT
            reviews.rating,
            reviews.review,
            reviews.created_at,
            users.name AS reviewer_name
        FROM reviews
        JOIN users
            ON reviews.reviewer_id = users.id
        WHERE reviews.reviewee_id = ?
        ORDER BY reviews.id DESC
    """, (creator["id"],)).fetchall()
@app.route("/review-creator/<int:request_id>", methods=["GET", "POST"])
def review_creator(request_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["user_role"] != "brand":
        return "Access denied", 403

    conn = db()

    # Check completed deal
    deal = conn.execute("""
        SELECT
            collaboration_requests.id,
            collaboration_requests.creator_id,
            campaigns.user_id AS brand_id,
            campaigns.brand_name,
            creators.name AS creator_name
        FROM collaboration_requests
        JOIN campaigns
            ON collaboration_requests.campaign_id = campaigns.id
        JOIN creators
            ON collaboration_requests.creator_id = creators.id
        WHERE collaboration_requests.id = ?
          AND campaigns.user_id = ?
          AND collaboration_requests.status = 'accepted'
          AND collaboration_requests.deal_status = 'completed'
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if not deal:
        conn.close()
        return "Deal not found or access denied", 404

    # Check if review already exists
    existing_review = conn.execute("""
        SELECT id
        FROM reviews
        WHERE request_id = ?
          AND reviewer_id = ?
        LIMIT 1
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if existing_review:
        conn.close()
        return "You have already reviewed this creator."

    if request.method == "POST":

        rating = request.form.get("rating")
        review_text = request.form.get("review", "").strip()

        if not rating:
            conn.close()
            return "Please select a rating.", 400

        try:
            rating = int(rating)
        except ValueError:
            conn.close()
            return "Invalid rating.", 400

        if rating < 1 or rating > 5:
            conn.close()
            return "Rating must be between 1 and 5.", 400

        conn.execute("""
            INSERT INTO reviews
            (request_id, reviewer_id, reviewee_id, rating, review)
            VALUES (?, ?, ?, ?, ?)
        """, (
            request_id,
            session["user_id"],
            deal["creator_id"],
            rating,
            review_text
        ))

        conn.commit()
        conn.close()

        return redirect(url_for(
            "brand_dashboard"
        ))

    conn.close()

    return render_template(
        "review_creator.html",
        deal=deal
    )
@app.route("/robots.txt")
def robots_txt():
    return "User-agent: *\nAllow: /\n", 200, {"Content-Type": "text/plain"}


connect_mongodb()
configure_cloudinary()
init_db()


if __name__ == "__main__":
    app.run(debug=True)
