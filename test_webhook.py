#!/usr/bin/env python3
# test_webhook.py - Script para probar webhook endpoint manualmente
"""
Script para probar la funcionalidad del webhook endpoint en desarrollo.
Simula las requests que Google Calendar enviaría en producción.
"""
import json
import requests
import time
from datetime import datetime


def test_webhook_endpoint():
    """Prueba el endpoint webhook con una request simulada."""
    
    webhook_url = "http://localhost:8001/webhook/calendar"
    
    # Headers que Google Calendar envía en webhooks reales
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Channel-ID': 'test-channel-id-12345',
        'X-Goog-Resource-ID': 'test-resource-id-67890', 
        'X-Goog-Resource-State': 'exists',  # 'exists', 'updated', 'sync'
        'X-Goog-Channel-Token': 'default-secret-token',
        'X-Goog-Message-Number': '1',
        'X-Goog-Resource-URI': 'https://www.googleapis.com/calendar/v3/calendars/test/events'
    }
    
    # Body de la request (Google Calendar webhooks normalmente vienen vacíos)
    data = {}
    
    print("🧪 Testing webhook endpoint...")
    print(f"📡 URL: {webhook_url}")
    print(f"📋 Headers: {json.dumps(headers, indent=2)}")
    
    try:
        # Enviar request al webhook
        response = requests.post(webhook_url, json=data, headers=headers, timeout=10)
        
        print(f"\n📤 Request sent at: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📥 Response status: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook endpoint responding correctly!")
            print("🔄 Check logs for sync processing details")
        else:
            print(f"⚠️ Unexpected response code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to webhook server")
        print("💡 Make sure the application is running: python main_dash.py")
        
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")


def test_webhook_status():
    """Prueba el endpoint de status del webhook."""
    
    status_url = "http://localhost:8001/webhook/status"
    
    print("\n🔍 Testing webhook status endpoint...")
    
    try:
        response = requests.get(status_url, timeout=5)
        
        print(f"📥 Status response: {response.status_code}")
        if response.status_code == 200:
            status_data = response.json()
            print(f"📊 Status data: {json.dumps(status_data, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")


def test_webhook_health():
    """Prueba el endpoint de health check."""
    
    health_url = "http://localhost:8001/health"
    
    print("\n💚 Testing health check endpoint...")
    
    try:
        response = requests.get(health_url, timeout=5)
        
        print(f"📥 Health response: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"🏥 Health data: {json.dumps(health_data, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error getting health: {e}")


if __name__ == "__main__":
    print("🚀 Webhook Testing Script")
    print("=" * 50)
    
    # Test all endpoints
    test_webhook_health()
    test_webhook_status() 
    test_webhook_endpoint()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
    print("\n💡 Instructions:")
    print("1. Start the app: python main_dash.py")
    print("2. Run this script: python test_webhook.py")
    print("3. Check logs for webhook processing")
    print("4. For production: use ngrok for HTTPS webhooks")