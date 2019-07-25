import pytest


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
                "Host": "wt6mne2s9k.execute-api.us-west-2.amazonaws.com",
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
                "apiId": "wt6mne2s9k",
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
                [b"host", b"wt6mne2s9k.execute-api.us-west-2.amazonaws.com"],
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
            "server": ("wt6mne2s9k.execute-api.us-west-2.amazonaws.com", 80),
            "type": "http",
        }

    @staticmethod
    def get_mock_SAM_template() -> str:
        return """AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
    TestProject
    ASGI application
Globals:
    Function:
        Timeout: 300
Resources:
    TestprojectFunction:
        Type: AWS::Serverless::Function
        Properties:
            FunctionName: TestprojectFunction
            CodeUri: ./build
            Handler: asgi.handler
            Runtime: python3.7
            # Environment:
            #     Variables:
            #         PARAM1: VALUE
            Events:
                Testproject:
                    Type: Api
                    Properties:
                        Path: /
                        Method: get
Outputs:
    TestprojectApi:
      Description: "API Gateway endpoint URL for Testproject function"
      Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/"
    TestprojectFunction:
      Description: "Testproject Lambda Function ARN"
      Value: !GetAtt TestprojectFunction.Arn
    TestprojectFunctionIamRole:
      Description: "Implicit IAM Role created for Testproject function"
      Value: !GetAtt TestprojectFunctionRole.Arn"""


@pytest.fixture
def mock_data():
    return MockData
