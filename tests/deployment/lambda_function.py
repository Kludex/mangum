import json


def lambda_handler(event, context):
    print("Event", json.dumps(event))
    return {
        'statusCode': 200,
        'headers':    {
            'content-type': 'application/json'
        },
        'body':       json.dumps(event)
    }
