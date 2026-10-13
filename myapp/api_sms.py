import requests
TERMII_API_KEY = "TLRbUaGTsMAiAKQMZxYOSHlOIFAeqbglGDPnPWExMvZEgNnoKSQNIeMkjNttiD"
SENDER_ID = "SchoolDevs"
def normalize_phone(number):
    number = str(number).strip().replace("`", "").replace(" ", "")

    if number.startswith("+"):
        number = number[1:]

    # Convert 080... to 23480...
    if number.startswith("0"):
        number = "234" + number[1:]

    # Validate NG number (234 + 10 digits = 13 digits)
    if len(number) != 13 or not number.isdigit():
        return None

    return number


def clean_phone_numbers(numbers):
    cleaned = set()
    for num in numbers:
        normalized = normalize_phone(num)
        if normalized:
            cleaned.add(normalized)
    return list(cleaned)

def send_sms_api(phone_numbers, message_text):
    results = {"success": [], "failed": []}

    # Normalize (keep duplicates if needed)
    phone_numbers = ["08140369543"]
    phone_numbers = [normalize_phone(n) for n in phone_numbers if normalize_phone(n)]
    print("Sending SMS to:", phone_numbers)

    for num in phone_numbers:
        url = "https://api.ng.termii.com/api/sms/send"
        payload = {
            "to": [num],
            "from": SENDER_ID,
            "sms": message_text,
            "type": "plain",
            "channel": "generic",
            "api_key": TERMII_API_KEY
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            res_json = response.json()

            if res_json.get("code") == "ok":
                results["success"].append(num)
                print("sent")
            else:
                results["failed"].append({
                    "number": num,
                    "error": res_json.get("message", "Unknown error")
                })

        except Exception as e:
            results["failed"].append({"number": num, "error": str(e)})

    return results
