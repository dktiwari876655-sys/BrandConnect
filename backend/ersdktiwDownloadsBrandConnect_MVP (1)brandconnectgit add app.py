warning: in the working copy of 'app.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/app.py b/app.py[m
[1mindex 8adaaca..9adec76 100644[m
[1m--- a/app.py[m
[1m+++ b/app.py[m
[36m@@ -2,10 +2,12 @@[m [mfrom flask import Flask, session, render_template, request, redirect, url_for, f[m
 from werkzeug.security import generate_password_hash, check_password_hash[m
 import sqlite3[m
 from pathlib import Path[m
[32m+[m[32mimport os[m
 import razorpay[m
 [m
[31m-RAZORPAY_KEY_ID = "rzp_test_TVC6gusYAazceK"[m
[31m-RAZORPAY_KEY_SECRET = "Nw7wjYMH4kDNfyA4UmxwGnWF"[m
[32m+[m[32mRAZORPAY_KEY_ID = os.environ.get("rzp_test_TXDoah1tOJAEBM")  # Replace with your Razorpay Key ID[m
[32m+[m[32mRAZORPAY_KEY_SECRET = os.environ.get("bWEp4uRskWGWciMIFAUg6Qec")[m
[32m+[m
 [m
 razorpay_client = razorpay.Client([m
     auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)[m
