  Project ID: kerala-red
  API Key: AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA
  Database: Firestore (default)
  Collection: "results"


   1. Get All Results (Latest 100):

  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/results?key=AIzaSyBECHTU    
  gMiedrtozaHGnyZHFv1pNLRaVqA

  2. Get Specific Lottery by Code:

  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/results/[CODE]?key=AIzaS    
  yBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA

  Example:
  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/results/ss-448?key=AIzaS    
  yBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA

  ---
  Problem: No "Today" Endpoint

  ❌ There is NO direct "today" or "daily result" 
  endpoint

  They organize data by lottery codes like:
  - ss-448 (Sthree Sakthi #448)
  - ak-099 (Akshaya #99)
  - kn-594 (Karunya Plus #594)

  ---
  How to Get Today's Result:

  Option 1: Query All Results and Filter

  curl "https://firestore.googleapis.com/v1/projects/kera    
  la-red/databases/(default)/documents/results?key=AIzaSy    
  BECHTUgMiedrtozaHGnyZHFv1pNLRaVqA&pageSize=20"

  Then in code, filter by today's date:
  import requests
  from datetime import datetime

  url = "https://firestore.googleapis.com/v1/projects/ker    
  ala-red/databases/(default)/documents/results"
  params = {
      'key': 'AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA',      
      'pageSize': 20
  }

  response = requests.get(url, params=params)
  data = response.json()

  today = datetime.now().strftime('%d/%m/%Y')

  for doc in data.get('documents', []):
      fields = doc['fields']
      date = fields.get('date', {}).get('stringValue',       
  '')
      if date == today:
          print(f"Found today's result: {fields}")
          break

  Option 2: Check Their "today" Document (if exists)

  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/today?key=AIzaSyBECHTUgM    
  iedrtozaHGnyZHFv1pNLRaVqA
  (I tested this - returns empty, they don't use it)

  ---
  Quick Test - Try These URLs:

  Get Latest Results:

  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/results?key=AIzaSyBECHTU    
  gMiedrtozaHGnyZHFv1pNLRaVqA&pageSize=5

  Get Specific Result (Example):

  https://firestore.googleapis.com/v1/projects/kerala-red    
  /databases/(default)/documents/results/ss-448?key=AIzaS    
  yBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA

  ---
  What My Scraper Does:

  In results/services/ponkudam_scraper.py, the
  _get_today_lottery_code() function:

  1. Fetches latest 10 results
  2. Looks for today's date (dd/mm/yyyy format)
  3. Returns the matching lottery code
  4. Falls back to most recent if today not found

  ---
  Summary:

  | What You Want    | API URL

                                                        |    
  |------------------|-----------------------------------    
  -------------------------------------------------------    
  ------------------------------------------------------|    
  | All Results      | https://firestore.googleapis.com/v    
  1/projects/kerala-red/databases/(default)/documents/res    
  ults?key=AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA      |    
  | Specific Lottery | https://firestore.googleapis.com/v    
  1/projects/kerala-red/databases/(default)/documents/res    
  ults/CODE?key=AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA |    
  | Today's Result   | ❌ No direct endpoint - must query     
   & filter by date

  |

  The API key is the same for all requests:
  AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA