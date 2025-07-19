#############################################################################
# Allocate an Elastic IP for the NAT Gateway
#############################################################################
resource "aws_eip" "nat" {
  domain = "vpc"   # use `domain` instead of deprecated `vpc = true`

  tags = {
    Name        = "nat-eip-${var.environment}"
    Environment = var.environment
  }
}

#############################################################################
# Create a NAT Gateway in one of your public subnets
#############################################################################
resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = module.vpc.public_subnet_ids[0]

  tags = {
    Name        = "natgw-${var.environment}"
    Environment = var.environment
  }
}

# Note: We’ve removed the aws_route.private_nat resource,
# since your aws_route_table.private already contains the 0.0.0.0/0 -> nat_gateway route.
