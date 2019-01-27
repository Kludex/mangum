import pytest


class MockData:
    @staticmethod
    def get_aws_event(body: str = "123", method: str = "GET") -> dict:
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
                "stage": "test",
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
            Handler: asgi.lambda_handler
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
