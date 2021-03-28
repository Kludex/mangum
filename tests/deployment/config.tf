locals {
  # Lambda@Edge can take forever to update, if you're not using it, just disable here.
  enable_lambda_at_edge = true
}
