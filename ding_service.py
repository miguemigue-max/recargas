# ding_service.py
from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

DING_API_KEY = ("CToM1v1Zhms6X84hQzKurD")

@app.route("/")
def home():
    return {"ok": True, "service": "ding"}

@app.route("/products/cuba")
def products_cuba():
    import requests

    url = "https://api.dingconnect.com/api/V1/GetProducts"
    headers = {
        "api_key": DING_API_KEY
    }

    try:
        res = requests.get(url, headers=headers, timeout=30)
        data = res.json()

        items = []

        for item in data.get("Items", []):
            # 🔍 Filtramos por Cuba (mejor por provider o texto)
            if "Cuba" in (item.get("DefaultDisplayText") or "") or item.get("RegionCode") == "CU":
                items.append({
                    "sku": item.get("SkuCode"),
                    "name": item.get("DefaultDisplayText"),
                    "price_usd": item.get("ReceiveValue"),
                    "send_value": item.get("SendValue"),
                    "send_currency": item.get("SendCurrencyIso")
                })

        return {
            "ok": True,
            "count": len(items),
            "items": items
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }, 500
        
@app.route("/send-topup", methods=["POST"])
def send_topup():
    data = request.get_json() or {}

    phone = (data.get("phone") or "").strip()
    sku_code = (data.get("sku_code") or "").strip()
    distributor_ref = (data.get("distributor_ref") or "").strip()

    if not phone or not sku_code or not distributor_ref:
        return jsonify({
            "ok": False,
            "error": "phone, sku_code y distributor_ref son requeridos"
        }), 400

    url = "https://api.dingconnect.com/api/V1/SendTransfer"
    headers = {
        "api_key": DING_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "SkuCode": sku_code,
        "AccountNumber": phone,
        "DistributorRef": distributor_ref
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        try:
            result = response.json()
        except Exception:
            result = {"raw": response.text}

        return jsonify({
            "ok": response.status_code in (200, 201),
            "status_code": response.status_code,
            "result": result
        }), response.status_code

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
