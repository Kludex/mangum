import base64
import json


def lambda_handler(event, context):
    print("Trigger Event", json.dumps(event))

    # Lambda@Edge is a special kind of special
    if "Records" in event and "cf" in event["Records"][0]:
        return {
            "status": 200,
            "headers": {
                "content-type": [{"key": "content-type", "value": "application/json"}]
            },
            "body": base64.b64encode(json.dumps(event).encode()).decode(),
            "bodyEncoding": "base64",
        }

    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(event),
    }
