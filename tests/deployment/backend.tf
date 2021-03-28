terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  # We are deploying to Lambda@Edge - this _must_ stay us-east-1
  region = "us-east-1"
}
