resource "aws_vpc" "mangum" {
  cidr_block = "10.254.254.0/24"
  tags = {
    Name = "test-mangum"
  }
}

resource "aws_subnet" "test_c" {
  cidr_block = "10.254.254.0/28"
  vpc_id = aws_vpc.mangum.id
  availability_zone = "us-east-1c"
}

resource "aws_subnet" "test_d" {
  cidr_block = "10.254.254.16/28"
  vpc_id = aws_vpc.mangum.id
  availability_zone = "us-east-1d"
}

resource "aws_internet_gateway" "mangum" {
  vpc_id = aws_vpc.mangum.id

  tags = {
    Name = "test-mangum"
  }
}

resource "aws_route" "mangum_igw" {
  route_table_id = aws_vpc.mangum.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.mangum.id
}
