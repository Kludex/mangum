import pytest
import os


class MockData:
    @staticmethod
    def get_aws_event(body: str = None, method: str = "GET") -> dict:
        event = {
            "path": "/test/hello",
            "body": body,
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
                "Accept-Language": "en-US,en;q=0.8",
                "CloudFront-Forwarded-Proto": "https",
                "CloudFront-Is-Desktop-Viewer": "true",
                "CloudFront-Is-Mobile-Viewer": "false",
                "CloudFront-Is-SmartTV-Viewer": "false",
                "CloudFront-Is-Tablet-Viewer": "false",
                "CloudFront-Viewer-Country": "US",
                "Host": "test.execute-api.us-west-2.amazonaws.com",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                "Via": "1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)",
                "X-Amz-Cf-Id": "nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==",
                "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
                "X-Forwarded-Port": "443",
                "X-Forwarded-Proto": "https",
            },
            "pathParameters": {"proxy": "hello"},
            "requestContext": {
                "accountId": "123456789012",
                "resourceId": "us4z18",
                "stage": "Prod",
                "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
                "identity": {
                    "cognitoIdentityPoolId": "",
                    "accountId": "",
                    "cognitoIdentityId": "",
                    "caller": "",
                    "apiKey": "",
                    "sourceIp": "192.168.100.1",
                    "cognitoAuthenticationType": "",
                    "cognitoAuthenticationProvider": "",
                    "userArn": "",
                    "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                    "user": "",
                },
                "resourcePath": "/{proxy+}",
                "httpMethod": method,
                "apiId": "test",
            },
            "resource": "/{proxy+}",
            "httpMethod": method,
            "queryStringParameters": {"name": "me"},
            "stageVariables": {"stageVarName": "stageVarValue"},
        }
        return event

    @staticmethod
    def get_aws_config_settings() -> dict:
        settings = {
            "project_name": "TestProject",
            "description": "ASGI application",
            "s3_bucket_name": "testproject-04a427ce-3267-4cbf-91c9-44fb986cddfd",
            "stack_name": "testproject",
            "resource_name": "Testproject",
            "url_root": "/",
            "runtime_version": "3.7",
            "region_name": "ap-southeast-1",
            "timeout": 300,
        }
        return settings

    @staticmethod
    def get_expected_scope() -> dict:
        return {
            "client": ("192.168.100.1", 0),
            "headers": [
                [
                    b"accept",
                    b"text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                    b"webp,*/*;q=0.8",
                ],
                [b"accept-encoding", b"gzip, deflate, lzma, sdch, br"],
                [b"accept-language", b"en-US,en;q=0.8"],
                [b"cloudfront-forwarded-proto", b"https"],
                [b"cloudfront-is-desktop-viewer", b"true"],
                [b"cloudfront-is-mobile-viewer", b"false"],
                [b"cloudfront-is-smarttv-viewer", b"false"],
                [b"cloudfront-is-tablet-viewer", b"false"],
                [b"cloudfront-viewer-country", b"US"],
                [b"host", b"test.execute-api.us-west-2.amazonaws.com"],
                [b"upgrade-insecure-requests", b"1"],
                [
                    b"user-agent",
                    b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/"
                    b"537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36"
                    b" OPR/39.0.2256.48",
                ],
                [
                    b"via",
                    b"1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFr"
                    b"ont)",
                ],
                [
                    b"x-amz-cf-id",
                    b"nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==",
                ],
                [b"x-forwarded-for", b"192.168.100.1, 192.168.1.1"],
                [b"x-forwarded-port", b"443"],
                [b"x-forwarded-proto", b"https"],
            ],
            "http_version": "1.1",
            "method": "GET",
            "path": "/test/hello",
            "query_string": b"name=me",
            "raw_path": None,
            "root_path": "Prod",
            "scheme": "https",
            "server": ("test.execute-api.us-west-2.amazonaws.com", 80),
            "type": "http",
        }


class MockWSConnection:
    def get_connect_event() -> dict:
        return {
            "headers": {
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Cookie": "pN=89; "
                "s_pers=%20s_vnum%3D1566262539670%2526vn%253D10%7C1566262539670%3B%20s_invisit%3Dtrue%7C1564884941744%3B%20s_nr%3D1564883141747-Repeat%7C1572659141747%3B; "
                "s_sess=%20s_cc%3Dtrue%3B%20s_sq%3D%3B",
                "Host": "test.execute-api.ap-southeast-1.amazonaws.com",
                "Origin": "https://2oz0a8hmz0.execute-api.ap-southeast-1.amazonaws.com",
                "Pragma": "no-cache",
                "Sec-WebSocket-Extensions": "permessage-deflate; "
                "client_max_window_bits",
                "Sec-WebSocket-Key": "bnfeqmh9SSPr5Sg9DvFIBw==",
                "Sec-WebSocket-Version": "13",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/75.0.3770.100 Safari/537.36",
                "X-Amzn-Trace-Id": "Root=1-5d465cb6-78ddcac1e21f89203d004a89",
                "X-Forwarded-For": "101.164.35.219",
                "X-Forwarded-Port": "443",
                "X-Forwarded-Proto": "https",
            },
            "isBase64Encoded": False,
            "multiValueHeaders": {
                "Accept-Encoding": ["gzip, deflate, br"],
                "Accept-Language": ["en-US,en;q=0.9"],
                "Cache-Control": ["no-cache"],
                "Cookie": [
                    "pN=89; "
                    "s_pers=%20s_vnum%3D1566262539670%2526vn%253D10%7C1566262539670%3B%20s_invisit%3Dtrue%7C1564884941744%3B%20s_nr%3D1564883141747-Repeat%7C1572659141747%3B; "
                    "s_sess=%20s_cc%3Dtrue%3B%20s_sq%3D%3B"
                ],
                "Host": ["test.execute-api.ap-southeast-1.amazonaws.com"],
                "Origin": [
                    "https://2oz0a8hmz0.execute-api.ap-southeast-1.amazonaws.com"
                ],
                "Pragma": ["no-cache"],
                "Sec-WebSocket-Extensions": [
                    "permessage-deflate; " "client_max_window_bits"
                ],
                "Sec-WebSocket-Key": ["bnfeqmh9SSPr5Sg9DvFIBw=="],
                "Sec-WebSocket-Version": ["13"],
                "User-Agent": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X "
                    "10_14_5) AppleWebKit/537.36 (KHTML, "
                    "like Gecko) Chrome/75.0.3770.100 "
                    "Safari/537.36"
                ],
                "X-Amzn-Trace-Id": ["Root=1-5d465cb6-78ddcac1e21f89203d004a89"],
                "X-Forwarded-For": ["101.164.35.219"],
                "X-Forwarded-Port": ["443"],
                "X-Forwarded-Proto": ["https"],
            },
            "requestContext": {
                "apiId": "test",
                "connectedAt": 1564892342293,
                "connectionId": "d4NsecoByQ0CH-Q=",
                "domainName": "test.execute-api.ap-southeast-1.amazonaws.com",
                "eventType": "CONNECT",
                "extendedRequestId": "d4NseGc4yQ0FsSA=",
                "identity": {
                    "accessKey": None,
                    "accountId": None,
                    "caller": None,
                    "cognitoAuthenticationProvider": None,
                    "cognitoAuthenticationType": None,
                    "cognitoIdentityId": None,
                    "cognitoIdentityPoolId": None,
                    "principalOrgId": None,
                    "sourceIp": "101.164.35.219",
                    "user": None,
                    "userAgent": "Mozilla/5.0 (Macintosh; Intel "
                    "Mac OS X 10_14_5) "
                    "AppleWebKit/537.36 (KHTML, like "
                    "Gecko) Chrome/75.0.3770.100 "
                    "Safari/537.36",
                    "userArn": None,
                },
                "messageDirection": "IN",
                "messageId": None,
                "requestId": "d4NseGc4yQ0FsSA=",
                "requestTime": "04/Aug/2019:04:19:02 +0000",
                "requestTimeEpoch": 1564892342293,
                "routeKey": "$connect",
                "stage": "Prod",
            },
        }

    def get_message_event() -> dict:
        return {
            "body": '{"action": "sendmessage", "data": "Hello world"}',
            "isBase64Encoded": False,
            "requestContext": {
                "apiId": "test",
                "connectedAt": 1564984321285,
                "connectionId": "d4NsecoByQ0CH-Q=",
                "domainName": "test.execute-api.ap-southeast-1.amazonaws.com",
                "eventType": "MESSAGE",
                "extendedRequestId": "d7uRtFvnyQ0FYmw=",
                "identity": {
                    "accessKey": None,
                    "accountId": None,
                    "caller": None,
                    "cognitoAuthenticationProvider": None,
                    "cognitoAuthenticationType": None,
                    "cognitoIdentityId": None,
                    "cognitoIdentityPoolId": None,
                    "principalOrgId": None,
                    "sourceIp": "101.164.35.219",
                    "user": None,
                    "userAgent": None,
                    "userArn": None,
                },
                "messageDirection": "IN",
                "messageId": "d7uRtfaKSQ0CE4Q=",
                "requestId": "d7uRtFvnyQ0FYmw=",
                "requestTime": "05/Aug/2019:05:52:10 +0000",
                "requestTimeEpoch": 1564984330952,
                "routeKey": "sendmessage",
                "stage": "Prod",
            },
        }


@pytest.fixture
def mock_data():
    return MockData


@pytest.fixture
def mock_ws() -> MockWSConnection:
    return MockWSConnection


def pytest_generate_tests(metafunc):
    os.environ["TABLE_NAME"] = "test-table"
