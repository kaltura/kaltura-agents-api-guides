#!/usr/bin/env python3
"""
Kaltura LMS Extensions — LTI Integration Demo

This app simulates a Learning Management System (like Canvas, Moodle, or Blackboard)
and demonstrates how Kaltura's LMS Extensions integrate with any LTI-compliant platform.

It shows how your platform communicates with Kaltura to embed video experiences
directly into your courses — without building anything from scratch.

Usage:
    pip install flask requests
    python app.py
    Open http://localhost:5050 in your browser.

Configuration (via .env or environment variables):
    KALTURA_PARTNER_ID     — Your Kaltura account ID
    KALTURA_ADMIN_SECRET   — Your admin secret (used for LTI signing)
    KALTURA_SERVICE_URL    — API endpoint (default: https://www.kaltura.com/api_v3)
"""

import os
import sys
import time
import uuid
import hashlib
import hmac as hmac_mod
import urllib.parse
import base64

from flask import (
    Flask, render_template_string, request, redirect, url_for, jsonify, session
)

# ─── Load .env ───────────────────────────────────────────────────────────────

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(__file__), "../../tests/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()

PARTNER_ID = os.environ.get("KALTURA_PARTNER_ID", "")
ADMIN_SECRET = os.environ.get("KALTURA_ADMIN_SECRET", "")
SERVICE_URL = os.environ.get("KALTURA_SERVICE_URL", "https://www.kaltura.com/api_v3")
KAF_BASE = f"https://{PARTNER_ID}.kaf.kaltura.com"
PUBLIC_URL = os.environ.get("PUBLIC_URL", "")

if not PARTNER_ID or not ADMIN_SECRET:
    print("ERROR: Set KALTURA_PARTNER_ID and KALTURA_ADMIN_SECRET")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.urandom(32)

caliper_events = []


@app.after_request
def set_headers(response):
    response.headers["Permissions-Policy"] = "camera=*, microphone=*, display-capture=*"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers.pop("X-Frame-Options", None)
    return response

# ─── LTI 1.1 Signing ─────────────────────────────────────────────────────────

def percent_encode(s):
    return urllib.parse.quote(str(s), safe="")


def sign_lti_launch(launch_url, params):
    """Generate OAuth 1.0a HMAC-SHA1 signature for LTI 1.1 launch."""
    params["oauth_consumer_key"] = PARTNER_ID
    params["oauth_signature_method"] = "HMAC-SHA1"
    params["oauth_timestamp"] = str(int(time.time()))
    params["oauth_nonce"] = uuid.uuid4().hex
    params["oauth_version"] = "1.0"

    sorted_params = sorted(params.items())
    param_string = "&".join(
        f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_params
    )
    base_string = f"POST&{percent_encode(launch_url)}&{percent_encode(param_string)}"
    signing_key = f"{percent_encode(ADMIN_SECRET)}&"
    signature = base64.b64encode(
        hmac_mod.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    params["oauth_signature"] = signature
    return params


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, kaf_base=KAF_BASE, partner_id=PARTNER_ID)


@app.route("/launch", methods=["POST"])
def launch():
    """Generate a signed LTI 1.1 launch form and auto-submit to KAF."""
    module = request.form.get("module", "my-media")
    role = request.form.get("role", "Instructor")
    user_id = request.form.get("user_id", "demo_instructor")
    context_id = request.form.get("context_id", "DEMO_COURSE_001")
    context_title = request.form.get("context_title", "Demo Course")

    module_endpoints = {
        "my-media": "/hosted/index/my-media",
        "course-gallery": "/hosted/index/course-gallery",
        "content-picker": "/browseandembed/index/browseandembed",
        "genie-ai": "/genie",
        "avatar-studio": "/avatarvodstudio/index/index",
        "meeting-room": "/embeddedrooms/index/view-room",
    }
    endpoint = module_endpoints.get(module, f"/hosted/index/{module}")
    launch_url = f"{KAF_BASE}{endpoint}"

    base_url = PUBLIC_URL.rstrip("/") if PUBLIC_URL else request.url_root.rstrip("/")

    params = {
        "lti_message_type": "basic-lti-launch-request",
        "lti_version": "LTI-1p0",
        "resource_link_id": f"demo_{module}_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "roles": role,
        "context_id": context_id,
        "context_title": context_title,
        "lis_person_name_full": f"Demo {role}",
        "lis_person_name_given": "Demo",
        "lis_person_name_family": role,
        "lis_person_contact_email_primary": f"{user_id}@example.com",
        "tool_consumer_instance_guid": "lti-sample-app.example.com",
        "tool_consumer_info_product_family_code": "kaltura-lti-demo",
        "launch_presentation_locale": "en-US",
        "launch_presentation_document_target": "iframe",
        "launch_presentation_return_url": f"{base_url}/deep-link-return",
    }

    params["custom_caliper_profile_url"] = f"{base_url}/caliper/profile"
    params["custom_caliper_federated_session_id"] = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
    params["lis_outcome_service_url"] = f"{base_url}/lti/outcomes"
    params["lis_result_sourcedid"] = f"{context_id}:{user_id}:demo_resource"

    if module == "content-picker":
        params["lti_message_type"] = "ContentItemSelectionRequest"
        params["content_item_return_url"] = f"{base_url}/deep-link-return"
        params["accept_media_types"] = "application/vnd.ims.lti.v1.ltilink"
        params["accept_presentation_document_targets"] = "iframe,window"

    if module == "meeting-room":
        params["roles"] = "Instructor"
        params["custom_entry_id"] = os.environ.get("KALTURA_MEETING_ROOM_ENTRY_ID", "YOUR_ROOM_ENTRY_ID")
        params["custom_room_moderator"] = "1"

    signed = sign_lti_launch(launch_url, params)

    friendly_names = {
        "my-media": "My Media",
        "course-gallery": "Media Gallery",
        "content-picker": "Content Picker",
        "genie-ai": "Genie AI",
        "avatar-studio": "Avatar Studio",
        "meeting-room": "Meeting Room",
    }
    friendly_roles = {
        "Instructor": "Instructor (full access)",
        "Learner": "Student (view only)",
        "Administrator": "Administrator",
        "TeachingAssistant": "Teaching Assistant",
    }

    return render_template_string(
        LAUNCH_HTML,
        launch_url=launch_url,
        params=signed,
        module=module,
        module_name=friendly_names.get(module, module),
        role=role,
        role_name=friendly_roles.get(role, role),
        context_id=context_id,
        context_title=context_title,
    )


@app.route("/deep-link-return", methods=["POST", "GET"])
def deep_link_return():
    """Receive content selection from Content Picker."""
    import json as json_mod, base64
    if request.method == "POST":
        data = dict(request.form)
        return render_template_string(DEEP_LINK_RETURN_HTML, data=data, in_iframe=True)
    encoded = request.args.get("d", "")
    if encoded:
        padded = encoded + "=" * (-len(encoded) % 4)
        data = json_mod.loads(base64.b64decode(padded).decode())
    else:
        data = {}
    return render_template_string(DEEP_LINK_RETURN_HTML, data=data, in_iframe=False)


@app.route("/how-it-works")
def how_it_works():
    """Explain how LTI works for non-technical users."""
    return render_template_string(HOW_IT_WORKS_HTML)


@app.route("/grade-passback")
def grade_passback():
    """Explain the grade sync flow."""
    return render_template_string(GRADE_PASSBACK_HTML, kaf_base=KAF_BASE)


@app.route("/ks-sso")
def ks_sso():
    """Demonstrate standalone embed without LTI."""
    import requests as req
    ks_resp = req.post(f"{SERVICE_URL}/service/session/action/start", data={
        "format": 1,
        "partnerId": PARTNER_ID,
        "secret": ADMIN_SECRET,
        "type": 0,
        "userId": "demo_ks_user",
        "expiry": 3600,
        "privileges": "disableentitlement",
    }, timeout=15)
    ks_token = ks_resp.json()
    embed_url = f"{KAF_BASE}/hosted/index/my-media/ks/{ks_token}"
    return render_template_string(KS_SSO_HTML, embed_url=embed_url, ks_token=str(ks_token))


@app.route("/provisioning")
def provisioning():
    """SIS provisioning console."""
    return render_template_string(PROVISIONING_HTML, service_url=SERVICE_URL)


@app.route("/api/sis/create-course", methods=["POST"])
def api_create_course():
    import requests as req
    data = request.json
    resp = req.post(f"{SERVICE_URL}/service/category/action/add", data={
        "ks": _generate_ks(),
        "format": 1,
        "category[name]": data.get("name", f"COURSE_{int(time.time())}"),
        "category[description]": data.get("description", ""),
    }, timeout=15)
    return jsonify(resp.json())


@app.route("/api/sis/enroll", methods=["POST"])
def api_enroll():
    import requests as req
    data = request.json
    resp = req.post(f"{SERVICE_URL}/service/categoryUser/action/add", data={
        "ks": _generate_ks(),
        "format": 1,
        "categoryUser[categoryId]": data["categoryId"],
        "categoryUser[userId]": data["userId"],
        "categoryUser[permissionLevel]": data.get("permissionLevel", "0"),
    }, timeout=15)
    return jsonify(resp.json())


@app.route("/api/sis/assign-content", methods=["POST"])
def api_assign_content():
    import requests as req
    data = request.json
    resp = req.post(f"{SERVICE_URL}/service/categoryEntry/action/add", data={
        "ks": _generate_ks(),
        "format": 1,
        "categoryEntry[categoryId]": data["categoryId"],
        "categoryEntry[entryId]": data["entryId"],
    }, timeout=15)
    return jsonify(resp.json())


@app.route("/caliper/profile")
def caliper_profile():
    """Return Caliper event store configuration (KAF calls this to discover where to send events)."""
    base_url = PUBLIC_URL.rstrip("/") if PUBLIC_URL else request.url_root.rstrip("/")
    return jsonify([{
        "id": f"{base_url}/caliper/events",
        "type": "EventStore",
        "apiKey": "demo-caliper-key-12345",
        "sendEvents": True,
        "sendEntities": True,
    }])


@app.route("/caliper/events", methods=["POST"])
def caliper_receive():
    """Receive Caliper events from KAF (acts as a mini Learning Record Store)."""
    import json as json_mod
    auth = request.headers.get("Authorization", "")
    if auth not in ("demo-caliper-key-12345", "no-scheme demo-caliper-key-12345"):
        return jsonify({"error": "unauthorized"}), 401
    payload = request.get_json(force=True, silent=True) or {}
    events = payload.get("data", [payload]) if "data" in payload else [payload]
    for event in events:
        caliper_events.append({
            "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": event,
        })
    if len(caliper_events) > 200:
        caliper_events[:] = caliper_events[-200:]
    return jsonify({"status": "ok", "received": len(events)})


@app.route("/caliper")
def caliper_viewer():
    """View received Caliper learning analytics events."""
    return render_template_string(CALIPER_HTML, events=caliper_events)


@app.route("/api/caliper/events")
def api_caliper_events():
    """JSON endpoint for polling Caliper events."""
    return jsonify(caliper_events[-50:])


@app.route("/lti/outcomes", methods=["POST"])
def lti_outcomes():
    """Receive LTI Basic Outcomes (grade passback from Kaltura IVQ)."""
    body = request.data.decode("utf-8")
    grade_entry = {
        "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content_type": request.content_type,
        "body": body[:2000],
    }
    caliper_events.append({
        "received_at": grade_entry["received_at"],
        "event": {"type": "LTI_GRADE_PASSBACK", "data": grade_entry},
    })
    return """<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeResponse xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader><imsx_POXResponseHeaderInfo>
    <imsx_version>V1.0</imsx_version>
    <imsx_messageIdentifier>1</imsx_messageIdentifier>
    <imsx_statusInfo><imsx_codeMajor>success</imsx_codeMajor></imsx_statusInfo>
  </imsx_POXResponseHeaderInfo></imsx_POXHeader>
  <imsx_POXBody><replaceResultResponse/></imsx_POXBody>
</imsx_POXEnvelopeResponse>""", 200, {"Content-Type": "application/xml"}


def _generate_ks():
    import requests as req
    resp = req.post(f"{SERVICE_URL}/service/session/action/start", data={
        "format": 1,
        "partnerId": PARTNER_ID,
        "secret": ADMIN_SECRET,
        "type": 2,
        "userId": "sis_admin",
        "expiry": 300,
        "privileges": "disableentitlement",
    }, timeout=15)
    return resp.json()


# ─── Shared CSS (Kaltura Brand Design System) ────────────────────────────────

BRAND_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;500;600;700;800;900&display=swap');

    :root {
        --brand-black: #282828;
        --brand-stream-blue: #006EFA;
        --brand-bubblegum-pink: #FF9DFF;
        --brand-tomato-red: #FF3D23;
        --brand-sunshine-yellow: #FFD357;
        --brand-apple-green: #5BC686;
        --brand-eggshell: #F8F8F5;
        --brand-teal: #00A078;
        --brand-amber: #FFAA00;

        --light-bg: #f8f9ff;
        --light-surface: #ffffff;
        --light-surface-low: #eff4ff;
        --light-surface-high: #dce9ff;
        --light-text: #0b1c30;
        --light-text-secondary: #464555;
        --light-border: #c7c4d8;
        --light-primary: #3525cd;

        --rounded-sm: 4px;
        --rounded-md: 8px;
        --rounded-lg: 12px;
        --rounded-full: 9999px;

        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        font-family: 'Lato', sans-serif;
        font-size: 15px;
        font-weight: 400;
        line-height: 1.5;
        color: var(--light-text);
        background: var(--light-bg);
    }

    h1 { font-size: 30px; font-weight: 800; line-height: 1.2; letter-spacing: -0.025em; }
    h2 { font-size: 20px; font-weight: 700; line-height: 1.3; }
    h3 { font-size: 18px; font-weight: 700; line-height: 1.4; }
    .eyebrow { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--light-text-secondary); }

    a { color: var(--brand-stream-blue); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .btn {
        display: inline-flex; align-items: center; justify-content: center;
        padding: 12px 20px; height: 40px;
        font-family: 'Lato', sans-serif; font-size: 14px; font-weight: 600;
        border: none; border-radius: var(--rounded-lg); cursor: pointer;
        transition: opacity 0.15s, transform 0.1s;
    }
    .btn:hover { opacity: 0.9; }
    .btn:active { transform: scale(0.98); }
    .btn-primary { background: var(--brand-stream-blue); color: #fff; }
    .btn-secondary { background: var(--light-surface); color: var(--light-text); border: 1px solid var(--light-border); }
    .btn-success { background: var(--brand-teal); color: #fff; }
    .btn-full { width: 100%; }

    .card {
        background: var(--light-surface);
        border: 1px solid rgba(199, 196, 216, 0.2);
        border-radius: var(--rounded-lg);
        padding: var(--space-lg);
        transition: box-shadow 0.2s;
    }
    .card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }

    .input-field {
        width: 100%; padding: 10px 14px; height: 40px;
        font-family: 'Lato', sans-serif; font-size: 15px;
        background: var(--light-surface); color: var(--light-text);
        border: 1px solid var(--light-border); border-radius: var(--rounded-lg);
    }
    .input-field:focus { outline: none; border-color: var(--brand-stream-blue); box-shadow: 0 0 0 2px rgba(0,110,250,0.15); }

    select.input-field { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23464555' d='M6 8L1 3h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 32px; }

    label { display: block; font-size: 14px; font-weight: 600; color: var(--light-text-secondary); margin-bottom: var(--space-xs); }

    .form-group { margin-bottom: var(--space-md); }

    .pill {
        display: inline-flex; align-items: center;
        padding: 4px 10px; border-radius: var(--rounded-full);
        font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
    }
    .pill-blue { background: #B6D7FF; color: #0b1c30; }
    .pill-green { background: #CEEEDB; color: #0b1c30; }
    .pill-yellow { background: #FFF2CD; color: #0b1c30; }
    .pill-pink { background: #FFE2FF; color: #0b1c30; }

    .container { max-width: 1100px; margin: 0 auto; padding: var(--space-xl); }
    .grid { display: grid; gap: var(--space-lg); }
    .grid-2 { grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }
    .grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }

    .header {
        background: var(--brand-black);
        color: #fff;
        padding: var(--space-xl) var(--space-xl) var(--space-lg);
    }
    .header p { color: rgba(255,255,255,0.75); margin-top: var(--space-sm); font-size: 15px; }

    .nav { display: flex; gap: var(--space-lg); margin-top: var(--space-md); flex-wrap: wrap; }
    .nav a { color: rgba(255,255,255,0.65); font-size: 14px; font-weight: 600; padding: var(--space-xs) 0; border-bottom: 2px solid transparent; }
    .nav a:hover, .nav a.active { color: #fff; border-bottom-color: var(--brand-amber); text-decoration: none; }

    .section-header { margin-bottom: var(--space-lg); }
    .section-header h2 { margin-bottom: var(--space-xs); }
    .section-header p { color: var(--light-text-secondary); }

    .callout {
        background: var(--light-surface-low);
        border-left: 4px solid var(--brand-stream-blue);
        padding: var(--space-md) var(--space-lg);
        border-radius: 0 var(--rounded-lg) var(--rounded-lg) 0;
        margin-bottom: var(--space-lg);
        font-size: 15px; line-height: 1.6;
    }
    .callout-warm { border-left-color: var(--brand-sunshine-yellow); background: #FFFCF0; }
    .callout-success { border-left-color: var(--brand-apple-green); background: #F0FFF6; }

    .step-number {
        display: inline-flex; align-items: center; justify-content: center;
        width: 28px; height: 28px; border-radius: var(--rounded-full);
        background: var(--brand-stream-blue); color: #fff;
        font-size: 14px; font-weight: 700; flex-shrink: 0;
    }

    .diagram {
        background: var(--light-surface);
        border: 1px solid rgba(199, 196, 216, 0.3);
        border-radius: var(--rounded-lg);
        padding: var(--space-lg);
        font-family: 'Lato', monospace;
        font-size: 14px;
        line-height: 1.8;
        overflow-x: auto;
        white-space: pre;
        color: var(--light-text-secondary);
    }
</style>
"""

# ─── HTML Templates ───────────────────────────────────────────────────────────

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kaltura LMS Extensions — LTI Integration Demo</title>
    """ + BRAND_CSS + """
    <style>
        .hero { text-align: center; padding: 48px 0 32px; }
        .hero h1 { font-size: 36px; margin-bottom: 12px; }
        .hero p { font-size: 17px; color: var(--light-text-secondary); max-width: 640px; margin: 0 auto; }
        .module-card { text-align: center; padding: var(--space-xl) var(--space-lg); }
        .module-card h3 { margin: 16px 0 8px; }
        .module-card p { font-size: 14px; color: var(--light-text-secondary); margin-bottom: 20px; min-height: 40px; }
        .module-icon { width: 56px; height: 56px; border-radius: var(--rounded-full); display: inline-flex; align-items: center; justify-content: center; font-size: 24px; }
        .module-icon-blue { background: #E8F2FF; }
        .module-icon-green { background: #E8FFF0; }
        .module-icon-yellow { background: #FFF9E8; }
        .options-toggle { font-size: 12px; color: var(--light-text-secondary); cursor: pointer; margin-top: 12px; border: none; background: none; font-family: 'Lato', sans-serif; text-decoration: underline; }
        .options-panel { display: none; text-align: left; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--light-border); }
        .how-banner { background: var(--light-surface-low); border-radius: var(--rounded-lg); padding: var(--space-lg) var(--space-xl); margin-top: 48px; text-align: center; }
        .how-banner p { color: var(--light-text-secondary); font-size: 15px; margin: 8px 0 16px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/" class="active">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <h1>Add Video to Any Learning Platform</h1>
            <p>This demo shows how Kaltura's video tools appear inside your LMS. Click a module below to launch it — exactly like a student or instructor would experience it.</p>
        </div>

        <div class="callout" style="max-width:700px;margin:0 auto 40px;">
            <strong>How it works:</strong> Your platform sends a signed message to Kaltura with the user's identity and course.
            Kaltura verifies it and shows the right video experience in an iframe. <a href="/how-it-works">Learn more &rarr;</a>
        </div>

        <div class="grid grid-3">
            <!-- My Media -->
            <div class="card module-card">
                <span class="module-icon module-icon-blue">&#128247;</span>
                <h3>My Media</h3>
                <p>Personal video library. Upload, record, and manage your own videos.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="my-media">
                    <input type="hidden" name="context_id" value="DEMO_COURSE_001">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="role" value="Instructor">
                    <button type="submit" class="btn btn-primary btn-full">Launch My Media</button>
                    <button type="button" class="options-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">Options</button>
                    <div class="options-panel">
                        <div class="form-group">
                            <label>Role</label>
                            <select name="role" class="input-field">
                                <option value="Instructor">Instructor</option>
                                <option value="Learner">Student</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>User ID</label>
                            <input type="text" name="user_id" value="demo_instructor" class="input-field">
                        </div>
                    </div>
                </form>
            </div>

            <!-- Media Gallery -->
            <div class="card module-card">
                <span class="module-icon module-icon-green">&#127891;</span>
                <h3>Media Gallery</h3>
                <p>Shared course library. Everyone in the same course sees the same videos.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="course-gallery">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="role" value="Instructor">
                    <input type="hidden" name="context_title" value="CS 201 — Data Structures">
                    <select name="context_id" class="input-field" style="margin-bottom:12px;" onchange="this.form.querySelector('input[name=context_title]').value=this.options[this.selectedIndex].text">
                        <option value="DEMO_CS_201">CS 201 — Data Structures</option>
                        <option value="DEMO_MATH_101">MATH 101 — Calculus I</option>
                        <option value="DEMO_ENG_301">ENG 301 — Technical Writing</option>
                    </select>
                    <button type="submit" class="btn btn-primary btn-full">Launch Media Gallery</button>
                    <button type="button" class="options-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">Options</button>
                    <div class="options-panel">
                        <div class="form-group">
                            <label>Role</label>
                            <select name="role" class="input-field">
                                <option value="Instructor">Instructor</option>
                                <option value="Learner">Student</option>
                            </select>
                        </div>
                    </div>
                </form>
            </div>

            <!-- Content Picker -->
            <div class="card module-card">
                <span class="module-icon module-icon-yellow">&#128206;</span>
                <h3>Content Picker</h3>
                <p>Browse videos and select one to embed in a page or assignment.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="content-picker">
                    <input type="hidden" name="role" value="Instructor">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="context_id" value="DEMO_COURSE_001">
                    <button type="submit" class="btn btn-primary btn-full">Open Content Picker</button>
                </form>
            </div>
        </div>

        <div class="section-header" style="margin-top:48px;">
            <h2>AI & Collaboration</h2>
            <p>Modules powered by Kaltura AI and real-time collaboration.</p>
        </div>

        <div class="grid grid-3">
            <!-- Genie AI -->
            <div class="card module-card">
                <span class="module-icon" style="background:#F0E8FF;">&#129302;</span>
                <h3>Genie AI</h3>
                <p>Conversational AI search across your video library. Ask questions, get answers from video content.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="genie-ai">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="role" value="Instructor">
                    <input type="hidden" name="context_id" value="DEMO_COURSE_001">
                    <button type="submit" class="btn btn-primary btn-full">Launch Genie AI</button>
                </form>
            </div>

            <!-- Avatar Studio -->
            <div class="card module-card">
                <span class="module-icon" style="background:#FFE8F0;">&#127917;</span>
                <h3>Avatar Studio</h3>
                <p>Create AI-generated avatar videos from text scripts. Choose a presenter and produce videos automatically.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="avatar-studio">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="role" value="Instructor">
                    <input type="hidden" name="context_id" value="DEMO_COURSE_001">
                    <button type="submit" class="btn btn-primary btn-full">Launch Avatar Studio</button>
                </form>
            </div>

            <!-- Meeting Room -->
            <div class="card module-card">
                <span class="module-icon" style="background:#E8FFF8;">&#128101;</span>
                <h3>Meeting Room</h3>
                <p>Live virtual classroom with video conferencing, screen sharing, whiteboard, and recording.</p>
                <form action="/launch" method="post">
                    <input type="hidden" name="module" value="meeting-room">
                    <input type="hidden" name="user_id" value="demo_instructor">
                    <input type="hidden" name="role" value="Instructor">
                    <input type="hidden" name="context_id" value="DEMO_COURSE_001">
                    <button type="submit" class="btn btn-primary btn-full">Launch Meeting Room</button>
                </form>
            </div>
        </div>

        <div class="callout" style="margin-top:48px;">
            <strong>Shared Repository</strong> — Access shared institutional media via the <strong>Content Picker</strong> above.
            When enabled in KAF admin, a "Shared Repository" tab appears in the Content Picker alongside My Media and Media Gallery tabs.
            It is not a standalone LTI placement — it's a content source within Browse &amp; Embed.
        </div>

        <div class="how-banner">
            <h2>Want to understand what happens behind the scenes?</h2>
            <p>See the signed messages, security model, course isolation, and role-based access explained in plain language.</p>
            <a href="/how-it-works" class="btn btn-secondary">How It Works &rarr;</a>
        </div>
    </div>
</body>
</html>
"""

LAUNCH_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ module_name }} — Kaltura LMS Extensions Demo</title>
    """ + BRAND_CSS + """
    <style>
        .toolbar { background: var(--brand-black); color: #fff; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; }
        .toolbar h2 { font-size: 16px; font-weight: 700; }
        .meta-bar { background: #1a1a2e; padding: 8px 24px; display: flex; gap: 20px; flex-wrap: wrap; align-items: center; font-size: 13px; color: rgba(255,255,255,0.5); }
        .meta-bar strong { color: rgba(255,255,255,0.85); font-weight: 600; }
        iframe { width: 100%; border: none; min-height: 800px; display: block; background: #fff; }
        .params-toggle { background: rgba(255,255,255,0.1); border: none; color: rgba(255,255,255,0.7); padding: 6px 12px; border-radius: var(--rounded-lg); cursor: pointer; font-size: 12px; font-weight: 600; font-family: 'Lato', sans-serif; }
        #params-panel { display: none; background: var(--light-surface); padding: 16px 24px; border-bottom: 1px solid var(--light-border); max-height: 250px; overflow-y: auto; }
        #params-panel table { width: 100%; font-size: 13px; border-collapse: collapse; }
        #params-panel td { padding: 4px 8px; border-bottom: 1px solid rgba(199,196,216,0.2); }
        #params-panel td:first-child { font-weight: 600; color: var(--brand-stream-blue); width: 220px; }
    </style>
</head>
<body>
    <div class="toolbar">
        <div style="display:flex;align-items:center;gap:12px;">
            <img src="/static/kaltura_sun_color.svg" alt="Kaltura" style="height:24px;width:24px;">
            <h2>{{ module_name }}</h2>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
            <button class="params-toggle" onclick="document.getElementById('params-panel').style.display = document.getElementById('params-panel').style.display === 'none' ? 'block' : 'none'">View LTI Parameters</button>
            <a href="/" style="color:rgba(255,255,255,0.7);font-size:13px;font-weight:600;text-decoration:none;">&larr; Dashboard</a>
        </div>
    </div>
    <div class="meta-bar">
        <span><strong>{{ role_name }}</strong></span>
        <span>Course: <strong>{{ context_title or context_id }}</strong></span>
    </div>

    <div id="params-panel">
        <p style="font-size:13px;color:var(--light-text-secondary);margin-bottom:8px;">
            These are the LTI parameters your platform sends to Kaltura. The OAuth signature proves this request is authentic.
        </p>
        <table>
        {% for key, value in params.items() %}
            <tr><td>{{ key }}</td><td>{{ value[:100] }}{% if value|length > 100 %}...{% endif %}</td></tr>
        {% endfor %}
        </table>
    </div>

    <iframe id="kaf-iframe" name="kaf-iframe" allow="camera *; microphone *; display-capture *; autoplay *; encrypted-media *; fullscreen *"></iframe>
    <form id="lti-form" method="POST" action="{{ launch_url }}" target="kaf-iframe" style="display:none;">
        {% for key, value in params.items() %}
        <input type="hidden" name="{{ key }}" value="{{ value }}">
        {% endfor %}
    </form>

    <script>
        document.getElementById("lti-form").submit();

        window.addEventListener("message", function(event) {
            if (!event.origin.includes("kaltura.com")) return;
            try {
                var parsed = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
                if (parsed.height) document.getElementById("kaf-iframe").style.height = parsed.height + "px";
            } catch(e) {}
        });
    </script>
</body>
</html>
"""

HOW_IT_WORKS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>How LTI Works — Kaltura LMS Extensions</title>
    """ + BRAND_CSS + """
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works" class="active">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container">
        <!-- What is LTI -->
        <div class="section-header">
            <h2>What is LTI?</h2>
        </div>
        <div class="callout">
            <strong>LTI (Learning Tools Interoperability)</strong> is a standard that lets learning platforms plug in external tools — like Kaltura — without custom coding.
            Think of it like a universal adapter: any LMS that speaks LTI can connect to any tool that speaks LTI. It handles authentication, user identity, and course context automatically.
        </div>

        <div class="grid grid-2" style="margin-top:24px;">
            <div class="card">
                <h3>Without LTI</h3>
                <ul style="margin-top:12px;padding-left:20px;color:var(--light-text-secondary);font-size:14px;line-height:2;">
                    <li>Build custom authentication</li>
                    <li>Manually sync users between systems</li>
                    <li>Write code to pass grades back</li>
                    <li>Build your own video upload UI</li>
                    <li>Manage content permissions yourself</li>
                </ul>
            </div>
            <div class="card" style="border-left:4px solid var(--brand-apple-green);">
                <h3>With LTI + Kaltura</h3>
                <ul style="margin-top:12px;padding-left:20px;color:var(--light-text-secondary);font-size:14px;line-height:2;">
                    <li>Authentication handled automatically</li>
                    <li>Users created on first visit</li>
                    <li>Grades flow back to your gradebook</li>
                    <li>Full video UI provided by Kaltura</li>
                    <li>Content isolated per-course automatically</li>
                </ul>
            </div>
        </div>

        <!-- The Flow -->
        <div class="section-header" style="margin-top:48px;">
            <h2>The Connection Flow</h2>
            <p>What happens when a user clicks a Kaltura link in your platform</p>
        </div>

        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">1</span>
                <div>
                    <h3 style="font-size:15px;">User clicks a Kaltura link</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">In the LMS course page, the user clicks "My Media" or "Media Gallery" or sees a video embedded by the instructor.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">2</span>
                <div>
                    <h3 style="font-size:15px;">Your platform constructs a signed message</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">The LMS packages user info (name, email, role), course info (course ID, title), and signs it with a shared secret so Kaltura can verify it's authentic.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">3</span>
                <div>
                    <h3 style="font-size:15px;">Kaltura verifies and renders</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Kaltura checks the signature, creates a session for the user, and shows the appropriate video module (library, gallery, picker, etc.) inside an iframe on your page.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;">
                <span class="step-number">4</span>
                <div>
                    <h3 style="font-size:15px;">Data flows back</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">If the user selects a video (Content Picker), takes a quiz, or completes an assignment, Kaltura sends data back to your platform — video details, quiz scores, or resize events.</p>
                </div>
            </div>
        </div>

        <div style="display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap;padding:32px 24px;background:var(--light-surface);border:1px solid rgba(199,196,216,0.3);border-radius:var(--rounded-lg);">
            <div style="background:var(--light-surface-low);border:2px solid var(--light-border);border-radius:var(--rounded-lg);padding:20px 24px;text-align:center;min-width:180px;">
                <div style="font-size:14px;font-weight:700;color:var(--light-text);">Your Platform</div>
                <div style="font-size:12px;color:var(--light-text-secondary);margin-top:4px;">LMS / LXP / Portal</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:160px;">
                <div style="font-size:12px;font-weight:600;color:var(--brand-stream-blue);">1. Signed LTI POST &rarr;</div>
                <div style="width:100%;height:2px;background:var(--brand-stream-blue);"></div>
                <div style="width:100%;height:2px;background:var(--brand-teal);margin-top:8px;"></div>
                <div style="font-size:12px;font-weight:600;color:var(--brand-teal);">&larr; 4. Grades, content, events</div>
            </div>
            <div style="background:var(--light-surface-low);border:2px solid var(--brand-stream-blue);border-radius:var(--rounded-lg);padding:20px 24px;text-align:center;min-width:180px;">
                <div style="font-size:14px;font-weight:700;color:var(--light-text);">Kaltura LMS Extensions</div>
                <div style="font-size:12px;color:var(--light-text-secondary);margin-top:4px;">Hosted by Kaltura</div>
                <div style="margin-top:12px;width:2px;height:20px;background:var(--light-border);margin-left:auto;margin-right:auto;"></div>
                <div style="font-size:11px;color:var(--light-text-secondary);margin-top:4px;">Uses Kaltura APIs</div>
                <div style="margin-top:4px;width:2px;height:20px;background:var(--light-border);margin-left:auto;margin-right:auto;"></div>
                <div style="background:var(--brand-black);color:#fff;border-radius:var(--rounded-md);padding:8px 12px;font-size:12px;font-weight:600;margin-top:4px;">Kaltura Platform<br><span style="font-weight:400;opacity:0.7;">Media, Search, AI, Analytics</span></div>
            </div>
        </div>

        <!-- What gets sent -->
        <div class="section-header" style="margin-top:48px;">
            <h2>What Your Platform Tells Kaltura</h2>
            <p>These are the key pieces of information included in every LTI launch</p>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <h3>User Identity</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.8;">
                    <strong>user_id</strong> — Unique identifier for this user<br>
                    <strong>lis_person_name_full</strong> — Display name<br>
                    <strong>lis_person_contact_email_primary</strong> — Email address<br>
                    <strong>roles</strong> — Instructor, Learner, Administrator, etc.
                </p>
            </div>
            <div class="card">
                <h3>Course Context</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.8;">
                    <strong>context_id</strong> — Unique course identifier (isolates content)<br>
                    <strong>context_title</strong> — Course name for display<br>
                    <strong>resource_link_id</strong> — Which tool placement was clicked<br>
                    <strong>launch_presentation_document_target</strong> — iframe or window
                </p>
            </div>
        </div>

        <!-- Security -->
        <div class="section-header" style="margin-top:48px;">
            <h2>Security — How Kaltura Verifies the Request</h2>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <span class="pill pill-blue" style="margin-bottom:12px;">LTI 1.1</span>
                <h3>Shared Secret (HMAC)</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.7;">
                    Both your platform and Kaltura know a shared secret. Your platform uses it to sign the request.
                    Kaltura uses the same secret to verify the signature matches. If someone tampers with the message, the signature won't match and the request is rejected.
                </p>
            </div>
            <div class="card">
                <span class="pill pill-green" style="margin-bottom:12px;">LTI 1.3</span>
                <h3>Public/Private Keys (JWT)</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.7;">
                    Your platform signs a token with its private key. Kaltura fetches your public key and verifies the token.
                    No shared secrets to manage — more secure, and required by newer LMS platforms.
                </p>
            </div>
        </div>

        <p style="margin-top:32px;text-align:center;"><a href="/" class="btn btn-secondary">Back to Demo Dashboard</a></p>
    </div>
</body>
</html>
"""

GRADE_PASSBACK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grade Sync — Kaltura LMS Extensions</title>
    """ + BRAND_CSS + """
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback" class="active">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container">
        <div class="callout callout-warm">
            <strong>Availability:</strong> Grade sync requires an LMS-specific profile (Canvas, Moodle, D2L, Blackboard, Sakai, or Schoology).
            The generic LTI profile does not include grade passback. If you need grades, ask your Kaltura representative to provision an LMS-specific instance.
        </div>

        <div class="section-header">
            <h2>The Grade Sync Flow</h2>
            <p>When a student takes an Interactive Video Quiz (IVQ) in Kaltura, their score can automatically appear in your gradebook.</p>
        </div>

        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">1</span>
                <div>
                    <h3 style="font-size:15px;">Instructor creates a video quiz</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Using Kaltura's quiz editor, the instructor adds questions at specific points in a video (multiple choice, true/false, reflection, etc.).</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">2</span>
                <div>
                    <h3 style="font-size:15px;">Student watches and answers</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">The video pauses at each question. The student answers inline, then continues watching. Kaltura calculates the score.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">3</span>
                <div>
                    <h3 style="font-size:15px;">Kaltura sends the grade to your LMS</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Kaltura authenticates to your platform's grade service and posts the score. The score appears in your gradebook just like any other assignment.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;">
                <span class="step-number">4</span>
                <div>
                    <h3 style="font-size:15px;">Score appears in the gradebook</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Students see their grade. Instructors see all scores in the standard gradebook view. No manual entry needed.</p>
                </div>
            </div>
        </div>

        <div style="display:flex;flex-direction:column;align-items:center;gap:0;padding:32px 24px;background:var(--light-surface);border:1px solid rgba(199,196,216,0.3);border-radius:var(--rounded-lg);">
            <div style="background:var(--light-surface-low);border:1px solid var(--light-border);border-radius:var(--rounded-md);padding:10px 20px;font-size:14px;font-weight:600;">Student watches quiz video</div>
            <div style="width:2px;height:20px;background:var(--light-border);"></div>
            <div style="background:#FFF9E8;border:1px solid var(--brand-sunshine-yellow);border-radius:var(--rounded-md);padding:10px 20px;font-size:14px;font-weight:600;">Kaltura calculates score (85/100)</div>
            <div style="width:2px;height:20px;background:var(--light-border);"></div>
            <div style="background:#E8F2FF;border:1px solid var(--brand-stream-blue);border-radius:var(--rounded-md);padding:10px 20px;font-size:14px;font-weight:600;">Kaltura &rarr; Your LMS grade service</div>
            <div style="width:2px;height:20px;background:var(--light-border);"></div>
            <div style="background:var(--light-surface-low);border:1px solid var(--light-border);border-radius:var(--rounded-md);padding:10px 20px;font-size:13px;color:var(--light-text-secondary);text-align:left;line-height:1.6;">
                Creates "Video Quiz" assignment (line item)<br>
                Posts score: 85/100 for Student A
            </div>
            <div style="width:2px;height:20px;background:var(--light-border);"></div>
            <div style="background:#E8FFF0;border:1px solid var(--brand-apple-green);border-radius:var(--rounded-md);padding:10px 20px;font-size:14px;font-weight:600;">Grade appears in LMS gradebook</div>
        </div>

        <div class="section-header" style="margin-top:48px;">
            <h2>Two Ways Grades Can Be Sent</h2>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <span class="pill pill-blue" style="margin-bottom:12px;">LTI 1.1</span>
                <h3>Basic Outcomes</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.7;">
                    Simple score passback. Sends a single number (0.0 to 1.0) back to the LMS.
                    Works with older platforms. Limited to one score per resource link.
                </p>
            </div>
            <div class="card" style="border-left:4px solid var(--brand-apple-green);">
                <span class="pill pill-green" style="margin-bottom:12px;">LTI 1.3</span>
                <h3>Assignment and Grade Services (AGS)</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.7;">
                    Full gradebook integration. Kaltura can create assignments, post scores with status (completed, in-progress),
                    and read back existing results. The modern approach used by Canvas, Moodle 4+, and Blackboard.
                </p>
            </div>
        </div>

        <p style="margin-top:32px;text-align:center;"><a href="/" class="btn btn-secondary">Back to Demo Dashboard</a></p>
    </div>
</body>
</html>
"""

KS_SSO_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Standalone Embed — Kaltura LMS Extensions</title>
    """ + BRAND_CSS + """
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso" class="active">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container">
        <div class="callout callout-warm">
            <strong>When to use this approach:</strong> Use standalone embed when your platform does not support LTI
            (for example, a corporate intranet, CRM, CMS, or custom portal). Instead of an LTI handshake,
            your server generates a session token and appends it to the Kaltura URL.
        </div>

        <div class="section-header">
            <h2>How It Works</h2>
        </div>

        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">1</span>
                <div>
                    <h3 style="font-size:15px;">Your server generates a session token</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Call the Kaltura API to create a short-lived session (KS) for the current user. This token expires in 1 hour.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:20px;">
                <span class="step-number">2</span>
                <div>
                    <h3 style="font-size:15px;">Append the token to the URL</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Add <code>/ks/{token}</code> to any Kaltura module URL. This authenticates the user without LTI.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;align-items:flex-start;">
                <span class="step-number">3</span>
                <div>
                    <h3 style="font-size:15px;">Embed in an iframe</h3>
                    <p style="color:var(--light-text-secondary);font-size:14px;margin-top:4px;">Place the URL in an iframe on your page. The user sees the full Kaltura experience.</p>
                </div>
            </div>
        </div>

        <div class="callout">
            <strong>Compatibility note:</strong> Standalone embed works only with Kaltura instances configured for token-based authentication (Jive, AEM, Salesforce, and custom configurations).
            LTI-based instances (Canvas, Moodle, generic LTI) require a signed LTI launch and will show "access denied" if you try this approach.
        </div>

        <div class="section-header" style="margin-top:24px;">
            <h2>Live Demo</h2>
            <p>We generated a session token and embedded the My Media module below.</p>
        </div>

        <div style="background:var(--light-surface);border:1px solid var(--light-border);border-radius:var(--rounded-lg);padding:12px 16px;margin-bottom:16px;font-size:13px;word-break:break-all;color:var(--light-text-secondary);">
            <strong style="color:var(--light-text);">Embed URL:</strong> {{ embed_url[:100] }}...
        </div>

        <iframe src="{{ embed_url }}" style="width:100%;min-height:500px;border:1px solid var(--light-border);border-radius:var(--rounded-lg);"></iframe>

        <div class="callout callout-warm" style="margin-top:16px;">
            If you see "access denied" above, that's expected. This demo instance uses LTI authentication,
            so it requires a signed LTI launch (which the main dashboard does).
            On an instance configured for token auth, the video library would appear here.
        </div>

        <p style="margin-top:32px;text-align:center;"><a href="/" class="btn btn-secondary">Back to Demo Dashboard</a></p>
    </div>
</body>
</html>
"""

PROVISIONING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Setup — Kaltura LMS Extensions</title>
    """ + BRAND_CSS + """
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning" class="active">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container">
        <div class="callout">
            <strong>When to use this:</strong> Kaltura automatically creates course spaces when users launch via LTI.
            However, if you want to <strong>pre-populate</strong> courses with content before anyone visits
            (for example, from a Student Information System during semester setup), you can use the Kaltura API directly.
        </div>

        <div class="section-header">
            <h2>Step-by-Step Course Provisioning</h2>
            <p>Each step below calls the live Kaltura API. Try them in order.</p>
        </div>

        <!-- Step 1: Create Course -->
        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                <span class="step-number">1</span>
                <h3>Create a Course</h3>
            </div>
            <p style="color:var(--light-text-secondary);font-size:14px;margin-bottom:16px;">
                This creates a category in Kaltura that represents a course. When students launch via LTI with the matching course ID, they'll see content from this category.
            </p>
            <div class="form-group">
                <label>Course Name</label>
                <input type="text" id="course-name" value="PHYSICS_101_Fall2026" class="input-field">
            </div>
            <div class="form-group">
                <label>Description</label>
                <input type="text" id="course-desc" value="Physics 101 — Introduction to Mechanics" class="input-field">
            </div>
            <button onclick="createCourse()" class="btn btn-primary">Create Course</button>
            <div class="result" id="course-result"></div>
        </div>

        <!-- Step 2: Enroll -->
        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                <span class="step-number">2</span>
                <h3>Enroll a Student</h3>
            </div>
            <p style="color:var(--light-text-secondary);font-size:14px;margin-bottom:16px;">
                This adds a user to the course with a specific permission level. The user will have access to course content when they launch via LTI.
            </p>
            <div class="form-group">
                <label>Course ID (from step 1)</label>
                <input type="text" id="enroll-cat" placeholder="Will auto-fill after step 1" class="input-field">
            </div>
            <div class="form-group">
                <label>Student ID</label>
                <input type="text" id="enroll-user" value="student@university.edu" class="input-field">
            </div>
            <div class="form-group">
                <label>Access Level</label>
                <select id="enroll-level" class="input-field">
                    <option value="0">Member — can view content</option>
                    <option value="2">Moderator — can manage content</option>
                    <option value="3">Manager — can manage members</option>
                </select>
            </div>
            <button onclick="enrollStudent()" class="btn btn-primary">Enroll Student</button>
            <div class="result" id="enroll-result"></div>
        </div>

        <!-- Step 3: Assign -->
        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                <span class="step-number">3</span>
                <h3>Add Content to the Course</h3>
            </div>
            <p style="color:var(--light-text-secondary);font-size:14px;margin-bottom:16px;">
                This links a video (by its entry ID) to the course. Students will see it in their Media Gallery when they launch via LTI.
            </p>
            <div class="form-group">
                <label>Course ID</label>
                <input type="text" id="assign-cat" placeholder="Will auto-fill after step 1" class="input-field">
            </div>
            <div class="form-group">
                <label>Video Entry ID</label>
                <input type="text" id="assign-entry" placeholder="e.g., 1_abc123xyz" class="input-field">
            </div>
            <button onclick="assignContent()" class="btn btn-primary">Assign Content</button>
            <div class="result" id="assign-result"></div>
        </div>

        <p style="margin-top:16px;text-align:center;"><a href="/" class="btn btn-secondary">Back to Demo Dashboard</a></p>
    </div>

    <style>
        .result { margin-top:12px; padding:12px 16px; background:var(--brand-black); color:var(--brand-apple-green); font-family:'Lato',monospace; font-size:13px; border-radius:var(--rounded-lg); white-space:pre-wrap; max-height:180px; overflow-y:auto; display:none; }
    </style>
    <script>
        async function createCourse() {
            var res = document.getElementById("course-result");
            res.style.display = "block"; res.textContent = "Creating course...";
            try {
                var resp = await fetch("/api/sis/create-course", { method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ name: document.getElementById("course-name").value, description: document.getElementById("course-desc").value }) });
                var data = await resp.json();
                res.textContent = JSON.stringify(data, null, 2);
                if (data.id) { document.getElementById("enroll-cat").value = data.id; document.getElementById("assign-cat").value = data.id; }
            } catch(e) { res.textContent = "Error: " + e.message; }
        }
        async function enrollStudent() {
            var res = document.getElementById("enroll-result");
            res.style.display = "block"; res.textContent = "Enrolling...";
            try {
                var resp = await fetch("/api/sis/enroll", { method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ categoryId: document.getElementById("enroll-cat").value, userId: document.getElementById("enroll-user").value, permissionLevel: document.getElementById("enroll-level").value }) });
                res.textContent = JSON.stringify(await resp.json(), null, 2);
            } catch(e) { res.textContent = "Error: " + e.message; }
        }
        async function assignContent() {
            var res = document.getElementById("assign-result");
            res.style.display = "block"; res.textContent = "Assigning...";
            try {
                var resp = await fetch("/api/sis/assign-content", { method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ categoryId: document.getElementById("assign-cat").value, entryId: document.getElementById("assign-entry").value }) });
                res.textContent = JSON.stringify(await resp.json(), null, 2);
            } catch(e) { res.textContent = "Error: " + e.message; }
        }
    </script>
</body>
</html>
"""

CALIPER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Learning Analytics (Caliper) — Kaltura LMS Extensions</title>
    """ + BRAND_CSS + """
    <style>
        .event-card { margin-bottom:12px; border-left:3px solid var(--brand-stream-blue); }
        .event-card pre { font-size:12px; line-height:1.5; overflow-x:auto; white-space:pre-wrap; word-break:break-all; max-height:200px; overflow-y:auto; background:var(--light-surface-low); padding:12px; border-radius:var(--rounded-md); margin-top:8px; }
        .event-time { font-size:12px; color:var(--light-text-secondary); }
        .event-type { font-weight:700; font-size:14px; }
        .no-events { text-align:center; padding:48px; color:var(--light-text-secondary); }
        #event-count { font-weight:700; color:var(--brand-stream-blue); }
    </style>
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper" class="active">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container">
        <div class="section-header">
            <h2>Learning Analytics Events (Caliper)</h2>
            <p>Real-time stream of learning events from Kaltura. Events appear here as users interact with video modules.</p>
        </div>

        <div class="callout">
            <strong>How this works:</strong> When you launch any module, our app provides Kaltura with a Caliper Profile URL
            (<code>custom_caliper_profile_url</code>). Kaltura calls that URL to discover our event store endpoint,
            then sends learning events (video played, paused, completed, quiz submitted) to that endpoint in real time.
        </div>

        <div class="card" style="margin-bottom:24px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span id="event-count">{{ events|length }}</span> events received
                </div>
                <button class="btn btn-secondary" onclick="refreshEvents()" style="height:32px;font-size:13px;">Refresh</button>
            </div>
        </div>

        <div id="events-container">
        {% if events %}
            {% for item in events|reverse %}
            <div class="card event-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span class="event-type">{{ item.event.get('type', item.event.get('@type', 'Event')) if item.event is mapping else 'Event' }}</span>
                    <span class="event-time">{{ item.received_at }}</span>
                </div>
                {% if item.event is mapping and item.event.get('action') %}
                <div style="margin-top:4px;font-size:13px;color:var(--light-text-secondary);">Action: <strong>{{ item.event.get('action') }}</strong></div>
                {% endif %}
                <pre>{{ item.event | tojson(indent=2) }}</pre>
            </div>
            {% endfor %}
        {% else %}
            <div class="no-events">
                <p style="font-size:18px;margin-bottom:8px;">No events yet</p>
                <p>Launch a module from the <a href="/">dashboard</a>, interact with it, and events will appear here.</p>
            </div>
        {% endif %}
        </div>

        <div class="section-header" style="margin-top:48px;">
            <h2>What is Caliper?</h2>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <h3>IMS Caliper Analytics</h3>
                <p style="color:var(--light-text-secondary);font-size:14px;margin-top:8px;line-height:1.7;">
                    An IMS Global standard for describing learning activities. When a student plays a video, pauses, seeks,
                    completes a quiz, or submits an assignment — each action becomes a structured event sent to your Learning Record Store (LRS).
                </p>
            </div>
            <div class="card">
                <h3>Event Types You'll See</h3>
                <ul style="margin-top:8px;padding-left:20px;color:var(--light-text-secondary);font-size:14px;line-height:2;">
                    <li><strong>MediaEvent</strong> — Video started, paused, resumed, ended</li>
                    <li><strong>NavigationEvent</strong> — User navigated to media</li>
                    <li><strong>AssessmentEvent</strong> — Quiz started, submitted</li>
                    <li><strong>GradeEvent</strong> — Score assigned</li>
                    <li><strong>SessionEvent</strong> — User logged in/out</li>
                </ul>
            </div>
        </div>

        <p style="margin-top:32px;text-align:center;"><a href="/" class="btn btn-secondary">Back to Demo Dashboard</a></p>
    </div>

    <script>
        async function refreshEvents() {
            var resp = await fetch("/api/caliper/events");
            var events = await resp.json();
            document.getElementById("event-count").textContent = events.length;
            if (events.length === 0) return;
            var container = document.getElementById("events-container");
            container.innerHTML = "";
            events.reverse().forEach(function(item) {
                var type = (item.event && (item.event.type || item.event["@type"])) || "Event";
                var action = (item.event && item.event.action) || "";
                var card = document.createElement("div");
                card.className = "card event-card";
                card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;"><span class="event-type">' + type + '</span><span class="event-time">' + item.received_at + '</span></div>' +
                    (action ? '<div style="margin-top:4px;font-size:13px;color:var(--light-text-secondary);">Action: <strong>' + action + '</strong></div>' : '') +
                    '<pre>' + JSON.stringify(item.event, null, 2) + '</pre>';
                container.appendChild(card);
            });
        }
        setInterval(refreshEvents, 10000);
    </script>
</body>
</html>
"""

DEEP_LINK_RETURN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Content Selected — Kaltura</title>
    """ + BRAND_CSS + """
    {% if in_iframe %}
    <script>
        // Break out of iframe — redirect top window to this same page with data in URL
        (function() {
            if (window.top !== window.self) {
                var data = {{ data | tojson | safe }};
                var encoded = btoa(unescape(encodeURIComponent(JSON.stringify(data))));
                window.top.location.href = window.location.origin + "/deep-link-return?d=" + encodeURIComponent(encoded);
            }
        })();
    </script>
    {% endif %}
</head>
<body>
    <div class="header">
        <div class="container" style="padding-top:0;padding-bottom:0;">
            <img src="/static/kaltura_logo_white.svg" alt="Kaltura" style="height:36px;margin-bottom:8px;">
            <nav class="nav">
                <a href="/">Try It</a>
                <a href="/how-it-works">How It Works</a>
                <a href="/grade-passback">Grade Sync</a>
                <a href="/caliper">Analytics</a>
                <a href="/ks-sso">Standalone Embed</a>
                <a href="/provisioning">Course Setup (API)</a>
            </nav>
        </div>
    </div>
    <div class="container" style="max-width:900px;">
        {% if data and data.get('content_items') %}
        <div class="callout callout-success" style="margin-top:24px;">
            <strong>Video embedded successfully.</strong> Kaltura returned the selected content. Below is how it would render in your platform.
        </div>

        <div class="card" style="margin-top:24px;padding:0;overflow:hidden;">
            <div id="embed-preview" style="width:100%;aspect-ratio:16/9;background:#000;"></div>
        </div>

        <div class="section-header" style="margin-top:32px;">
            <h2>What Kaltura Returned</h2>
            <p>Your platform uses this data to store and render the embedded video.</p>
        </div>

        <div class="card">
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
            {% for key, value in data.items() %}
                <tr>
                    <td style="padding:8px;border-bottom:1px solid rgba(199,196,216,0.2);font-weight:600;width:200px;vertical-align:top;">{{ key }}</td>
                    <td style="padding:8px;border-bottom:1px solid rgba(199,196,216,0.2);word-break:break-all;">{{ value[:300] }}</td>
                </tr>
            {% endfor %}
            </table>
        </div>

        <script>
            try {
                var items = JSON.parse({{ data.get("content_items", "{}") | tojson | safe }});
                var graph = items["@graph"] || [];
                if (graph.length > 0) {
                    var url = graph[0].url;
                    if (url) {
                        var iframe = document.createElement("iframe");
                        iframe.src = url;
                        iframe.style.cssText = "width:100%;height:100%;border:none;";
                        iframe.allow = "autoplay; encrypted-media; fullscreen";
                        document.getElementById("embed-preview").appendChild(iframe);
                    }
                }
            } catch(e) { console.log("Could not parse content_items:", e); }
        </script>
        {% elif data %}
        <div class="card" style="margin-top:24px;">
            <h2 style="margin-bottom:16px;">Content Selected</h2>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
            {% for key, value in data.items() %}
                <tr>
                    <td style="padding:8px;border-bottom:1px solid rgba(199,196,216,0.2);font-weight:600;width:200px;">{{ key }}</td>
                    <td style="padding:8px;border-bottom:1px solid rgba(199,196,216,0.2);word-break:break-all;">{{ value[:300] }}</td>
                </tr>
            {% endfor %}
            </table>
        </div>
        {% else %}
        <div class="card" style="margin-top:48px;">
            <h2 style="margin-bottom:16px;">Content Selected</h2>
            <div class="callout callout-warm">
                No data received. This can happen if the user cancelled the selection or if the Content Picker is not yet configured for return URLs in this instance.
            </div>
        </div>
        {% endif %}
        <p style="margin-top:32px;text-align:center;"><a href="/" class="btn btn-secondary">&larr; Back to Dashboard</a></p>
    </div>
</body>
</html>
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n{'=' * 60}")
    print(f"  Kaltura LMS Extensions — LTI Integration Demo")
    print(f"  Instance: {KAF_BASE}")
    print(f"  Partner:  {PARTNER_ID}")
    print(f"{'=' * 60}")
    print(f"\n  Open http://localhost:{port} in your browser\n")
    app.run(host="0.0.0.0", port=port, debug=True)
