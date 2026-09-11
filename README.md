# BrandConnect

A starter MVP for a marketplace connecting small brands with affordable YouTube/Instagram creators.

## Run locally

1. Open this folder in VS Code.
2. Create/activate a virtual environment (optional but recommended).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start:

```bash
python app.py
```

5. Open the local address shown by Flask (usually http://127.0.0.1:5000).

## MongoDB and Cloudinary

1. Copy `backend/.env.example` to `backend/.env`.
2. Create a MongoDB Atlas database and paste its connection string into `MONGO_URI`.
3. Create a Cloudinary account and add `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`.
4. Add a strong `FLASK_SECRET_KEY` and your Razorpay credentials.

MongoDB stores a synchronized copy of creator profiles. Existing marketplace, campaign, chat, and payment flows continue using the app's current SQLite database. Creator profile images are uploaded to Cloudinary and their secure URLs are saved in both stores.

Integration code is separated into `backend/mongo_service.py` and `backend/cloudinary_service.py`; `backend/app.py` only calls these services.

## Pages

- `/` — Home
- `/creators` — Creator marketplace with filters
- `/campaign` — Brand campaign form
- `/matches/<campaign_id>` — Budget/category matching
- `/admin` — Simple admin overview

This is an educational MVP. Authentication, real payments, creator verification, messaging, production security, and legal/privacy controls should be added before real deployment.
