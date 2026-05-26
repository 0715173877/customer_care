#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL.
Reads from db.sqlite3 and writes to the Django ORM (currently connected to PostgreSQL).
Handles schema differences between old SQLite tables and current Django models.
Run: python manage.py migrate && python migrate_data.py
"""

import os
import sys
import sqlite3
import json as _json
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "customer_care.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from payments.models import PaymentRequest
from calls.models import CallLog, CallMenuOption
from sms_app.models import SMSMessage, SMSAutoReply
from chatbot.models import Conversation, Message, KnowledgeBase

User = get_user_model()

# Connect to SQLite
sqlite_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")
conn = sqlite3.connect(sqlite_path)
conn.row_factory = sqlite3.Row

print("Starting data migration from SQLite to PostgreSQL...")
print("=" * 60)

# 1. Migrate users
print("\n--- Users ---")
sqlite_users = conn.execute("SELECT * FROM auth_user").fetchall()
user_map = {}
for u in sqlite_users:
    user, created = User.objects.get_or_create(
        username=u["username"],
        defaults={
            "password": u["password"],
            "email": u["email"],
            "is_superuser": bool(u["is_superuser"]),
            "is_staff": bool(u["is_staff"]),
            "is_active": bool(u["is_active"]),
            "date_joined": u["date_joined"],
        }
    )
    user_map[u["id"]] = user
    status = "migrated" if created else "already exists"
    print(f"  '{user.username}' (old_id={u['id']} -> pk={user.pk}) - {status}")

# 2. Migrate PaymentRequests (same schema in both databases)
print("\n--- Payment Requests ---")
sqlite_pr = conn.execute("SELECT * FROM payments_paymentrequest").fetchall()
migrated_ct = 0
for pr in sqlite_pr:
    try:
        obj, created = PaymentRequest.objects.update_or_create(
            id=pr["id"],
            defaults={
                "status": pr["status"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "raw_sms": pr["raw_sms"],
                "amount": pr["amount"],
                "currency": pr["currency"],
                "sender_name": pr["sender_name"],
                "from_account": pr["from_account"],
                "from_account_type": pr["from_account_type"],
                "from_bank": pr["from_bank"],
                "receiver_name": pr["receiver_name"],
                "to_account": pr["to_account"],
                "to_account_type": pr["to_account_type"],
                "to_bank": pr["to_bank"],
                "reference": pr["reference"] or "",
                "memo": pr["memo"],
                "transaction_date": pr["transaction_date"],
                "parse_confidence": pr["parse_confidence"],
                "parse_notes": pr["parse_notes"],
                "reviewed_at": pr["reviewed_at"],
                "review_notes": pr["review_notes"],
                "authorized_at": pr["authorized_at"],
                "authorization_notes": pr["authorization_notes"],
                "ip_address": pr["ip_address"],
                "reviewed_by": user_map.get(pr["reviewed_by_id"]),
                "authorized_by": user_map.get(pr["authorized_by_id"]),
            }
        )
        migrated_ct += 1
        short = pr["raw_sms"][:60] if pr["raw_sms"] else "N/A"
        print(f"  ✓ {pr['id'][:8]}...")
    except Exception as e:
        print(f"  ✗ {pr['id'][:8]}... ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_pr)} migrated")

# 3. Migrate CallLogs (same field names in both)
print("\n--- Call Logs ---")
sqlite_cl = conn.execute("SELECT * FROM calls_calllog").fetchall()
migrated_ct = 0
for cl in sqlite_cl:
    try:
        obj, created = CallLog.objects.update_or_create(
            id=cl["id"],
            defaults={
                "call_sid": cl["call_sid"],
                "caller_number": cl["caller_number"],
                "recipient_number": cl["recipient_number"],
                "direction": cl["direction"],
                "status": cl["status"],
                "duration": cl["duration"],
                "summary": cl["summary"],
                "intent_detected": cl["intent_detected"],
                "created_at": cl["created_at"],
                "updated_at": cl["updated_at"],
            }
        )
        migrated_ct += 1
        print(f"  ✓ Call id={cl['id']} from {cl['caller_number']}")
    except Exception as e:
        print(f"  ✗ Call id={cl['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_cl)} migrated")

# 4. Migrate CallMenuOptions (same field names)
print("\n--- Call Menu Options ---")
sqlite_cmo = conn.execute("SELECT * FROM calls_callmenuoption").fetchall()
migrated_ct = 0
for cmo in sqlite_cmo:
    try:
        obj, created = CallMenuOption.objects.update_or_create(
            id=cmo["id"],
            defaults={
                "digit": cmo["digit"],
                "title": cmo["title"],
                "description": cmo["description"],
                "is_active": bool(cmo["is_active"]),
                "order": cmo["order"],
                "created_at": cmo["created_at"],
            }
        )
        migrated_ct += 1
        print(f"  ✓ MenuOption digit={cmo['digit']} - {cmo['title']}")
    except Exception as e:
        print(f"  ✗ MenuOption id={cmo['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_cmo)} migrated")

# 5. Migrate SMSMessages (same field names)
print("\n--- SMS Messages ---")
sqlite_sms = conn.execute("SELECT * FROM sms_app_smsmessage").fetchall()
migrated_ct = 0
for sms in sqlite_sms:
    try:
        obj, created = SMSMessage.objects.update_or_create(
            id=sms["id"],
            defaults={
                "message_sid": sms["message_sid"],
                "from_number": sms["from_number"].strip(),
                "to_number": sms["to_number"].strip(),
                "body": sms["body"],
                "direction": sms["direction"],
                "status": sms["status"],
                "is_automated": bool(sms["is_automated"]),
                "auto_reply": sms["auto_reply"],
                "intent_detected": sms["intent_detected"],
                "created_at": sms["created_at"],
                "updated_at": sms["updated_at"],
            }
        )
        migrated_ct += 1
        short = sms["body"][:50] if sms["body"] else "N/A"
        print(f"  ✓ SMS id={sms['id']} {sms['direction']}: {short}")
    except Exception as e:
        print(f"  ✗ SMS id={sms['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_sms)} migrated")

# 6. Migrate SMSAutoReplies (same field names)
print("\n--- SMS Auto Replies ---")
sqlite_sar = conn.execute("SELECT * FROM sms_app_smsautoreply").fetchall()
migrated_ct = 0
for sar in sqlite_sar:
    try:
        obj, created = SMSAutoReply.objects.update_or_create(
            id=sar["id"],
            defaults={
                "keyword": sar["keyword"],
                "reply_text": sar["reply_text"],
                "is_active": bool(sar["is_active"]),
                "created_at": sar["created_at"],
                "updated_at": sar["updated_at"],
            }
        )
        migrated_ct += 1
        print(f"  ✓ AutoReply keyword='{sar['keyword']}'")
    except Exception as e:
        print(f"  ✗ AutoReply id={sar['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_sar)} migrated")

# 7. Migrate Conversations (same field names)
print("\n--- Conversations ---")
sqlite_conv = conn.execute("SELECT * FROM chatbot_conversation").fetchall()
conv_map = {}
migrated_ct = 0
for c in sqlite_conv:
    try:
        # Parse intent_history JSON field
        intent_history = []
        raw = c["intent_history"]
        if raw:
            try:
                intent_history = _json.loads(raw) if isinstance(raw, str) else raw
            except:
                intent_history = [raw]
        
        obj, created = Conversation.objects.update_or_create(
            session_id=c["session_id"],
            defaults={
                "user_identifier": c["user_identifier"],
                "intent_history": intent_history,
                "is_active": bool(c["is_active"]),
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
            }
        )
        conv_map[c["id"]] = obj
        migrated_ct += 1
        print(f"  ✓ Conversation session={c['session_id'][:30]}...")
    except Exception as e:
        print(f"  ✗ Conversation id={c['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_conv)} migrated")

# 8. Migrate Messages (same field names)
print("\n--- Messages ---")
sqlite_msg = conn.execute("SELECT * FROM chatbot_message").fetchall()
migrated_ct = 0
skipped_ct = 0
for m in sqlite_msg:
    conv = conv_map.get(m["conversation_id"])
    if not conv:
        skipped_ct += 1
        continue
    try:
        obj, created = Message.objects.update_or_create(
            id=m["id"],
            defaults={
                "conversation": conv,
                "content": m["content"],
                "role": m["role"],
                "intent": m["intent"],
                "created_at": m["created_at"],
            }
        )
        migrated_ct += 1
    except Exception as e:
        print(f"  ✗ Message id={m['id']} ERROR: {e}")
print(f"  Total: {migrated_ct} migrated, {skipped_ct} skipped ({len(sqlite_msg)} total)")

# 9. Migrate KnowledgeBase (same field names)
print("\n--- Knowledge Base ---")
sqlite_kb = conn.execute("SELECT * FROM chatbot_knowledgebase").fetchall()
migrated_ct = 0
for kb in sqlite_kb:
    try:
        obj, created = KnowledgeBase.objects.update_or_create(
            id=kb["id"],
            defaults={
                "question": kb["question"],
                "answer": kb["answer"],
                "category": kb["category"],
                "keywords": kb["keywords"],
                "is_active": bool(kb["is_active"]),
                "created_at": kb["created_at"],
                "updated_at": kb["updated_at"],
            }
        )
        migrated_ct += 1
        short = kb["question"][:50] if kb["question"] else "N/A"
        print(f"  ✓ KB id={kb['id']}: {short}")
    except Exception as e:
        print(f"  ✗ KB id={kb['id']} ERROR: {e}")
print(f"  Total: {migrated_ct}/{len(sqlite_kb)} migrated")

conn.close()
print("\n" + "=" * 60)
print("✅ Data migration complete!")
print("=" * 60)
