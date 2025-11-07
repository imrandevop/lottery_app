#!/usr/bin/env python
"""
Test script for Live Scraper Polling Endpoint

Usage:
    python test_polling_endpoint.py <YOUR_APP_URL> <YOUR_API_TOKEN>

Example:
    python test_polling_endpoint.py https://sea-lion-app-begbw.ondigitalocean.app ROEQoA7Wmrqh_b-riXXribsCDcj8XIMAmElhDrNoCnA
"""

import sys
import requests
import json
from datetime import datetime


def test_polling_endpoint(app_url, api_token):
    """Test the polling endpoint"""

    # Construct full URL
    if not app_url.startswith('http'):
        app_url = f'https://{app_url}'

    if not app_url.endswith('/'):
        app_url += '/'

    endpoint = f'{app_url}results/api/poll-sessions/'

    print("=" * 60)
    print("Testing Live Scraper Polling Endpoint")
    print("=" * 60)
    print(f"URL: {endpoint}")
    print(f"Token: {api_token[:10]}...{api_token[-10:]}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # Prepare headers
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }

    print("Sending POST request...")

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            timeout=60
        )

        print(f"Status Code: {response.status_code}")
        print()

        # Parse response
        try:
            data = response.json()
            print("Response:")
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Response (plain text):")
            print(response.text)

        print()
        print("=" * 60)

        # Interpret results
        if response.status_code == 200:
            print("✅ SUCCESS - Endpoint is working correctly!")
            print()
            print("Next steps:")
            print("1. Go to your Django admin panel")
            print("2. Start live scraping with a lottery URL")
            print("3. Wait 1-2 minutes for Cron-Job.org to trigger")
            print("4. Check if new prizes appear")

        elif response.status_code == 401:
            print("❌ UNAUTHORIZED - Token is invalid")
            print()
            print("Possible fixes:")
            print("1. Check that SCRAPER_API_TOKEN is set in DigitalOcean")
            print("2. Verify token matches exactly (no extra spaces)")
            print("3. Regenerate token if needed")

        elif response.status_code == 429:
            print("⚠️  TOO MANY REQUESTS - Another polling is in progress")
            print()
            print("This is normal if:")
            print("- Previous request is still running")
            print("- You're testing multiple times quickly")
            print("Wait 2 minutes and try again")

        elif response.status_code == 408:
            print("⚠️  TIMEOUT - Request took too long")
            print()
            print("Possible causes:")
            print("- Kerala lottery website is slow")
            print("- Too many active sessions")
            print("Try again in a few minutes")

        elif response.status_code == 500:
            print("❌ SERVER ERROR - Something went wrong")
            print()
            print("Check:")
            print("1. DigitalOcean Runtime Logs")
            print("2. Database connection")
            print("3. SCRAPER_API_TOKEN is set correctly")

        else:
            print(f"⚠️  UNEXPECTED STATUS: {response.status_code}")
            print()
            print("Check DigitalOcean logs for details")

        print("=" * 60)

        return response.status_code == 200

    except requests.ConnectionError:
        print("❌ CONNECTION ERROR")
        print()
        print("Could not connect to the server.")
        print("Check that:")
        print("1. App URL is correct")
        print("2. App is deployed and running")
        print("3. You have internet connection")
        return False

    except requests.Timeout:
        print("❌ TIMEOUT")
        print()
        print("Request took longer than 60 seconds.")
        print("This might indicate a problem with the scraping process.")
        return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python test_polling_endpoint.py <APP_URL> <API_TOKEN>")
        print()
        print("Example:")
        print("  python test_polling_endpoint.py https://sea-lion-app-begbw.ondigitalocean.app ROEQoA7Wmrqh_b-riXXribsCDcj8XIMAmElhDrNoCnA")
        print()
        print("Or:")
        print("  python test_polling_endpoint.py sea-lion-app-begbw.ondigitalocean.app YOUR_TOKEN")
        sys.exit(1)

    app_url = sys.argv[1]
    api_token = sys.argv[2]

    success = test_polling_endpoint(app_url, api_token)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
