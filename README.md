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

## Pages

- `/` — Home
- `/creators` — Creator marketplace with filters
- `/campaign` — Brand campaign form
- `/matches/<campaign_id>` — Budget/category matching
- `/admin` — Simple admin overview

This is an educational MVP. Authentication, real payments, creator verification, messaging, production security, and legal/privacy controls should be added before real deployment.
