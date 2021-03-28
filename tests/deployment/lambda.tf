data "aws_iam_policy_document" "lambda_fn_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]
    effect = "Allow"

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
        "edgelambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "mangum" {
  name = "test-mangum"
  assume_role_policy = data.aws_iam_policy_document.lambda_fn_assume_role.json
}

resource "aws_iam_role_policy_attachment" "mangum_lambda_basic" {
  role = aws_iam_role.mangum.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda" {
  type = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/lambda_code.zip"
}

resource "aws_lambda_function" "mangum" {
  function_name = "test-mangum"
  handler = "lambda_function.lambda_handler"
  role = aws_iam_role.mangum.arn
  runtime = "python3.7"

  filename = data.archive_file.lambda.output_path
  source_code_hash = filebase64sha256(data.archive_file.lambda.output_path)

  publish = true

  # Lambda@Edge functions cannot have environment variables
  # environment {
  #  variables = {
  #    TEST_FOO = "bar"
  #  }
  #}

  lifecycle {
    ignore_changes = [filename]
  }
}

# Create log group here so we can set retention and can clean it up.
resource "aws_cloudwatch_log_group" "mangum_logs" {
  name = "/aws/lambda/test-mangum"
  retention_in_days = "7"
}
