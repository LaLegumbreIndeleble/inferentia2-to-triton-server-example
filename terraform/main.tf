terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.52.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

provider "aws" {
  region = var.aws_region
}

# ============================================================
# VPC — single public subnet, simplest possible setup
# ============================================================

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.6.1"

  name = "neuron-vpc"
  cidr = "10.0.0.0/16"

  azs            = ["${var.aws_region}b"]
  public_subnets = ["10.0.1.0/24"]

  enable_nat_gateway = false
  enable_vpn_gateway = false

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}

# ============================================================
# Security group — SSH in, all out
# ============================================================

resource "aws_security_group" "neuron_sg" {
  name        = "neuron-test-sg"
  description = "Allow SSH inbound, all outbound"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ============================================================
# Key pair — existing "GGEZ" key (key-03b473)
# ============================================================

data "aws_key_pair" "ggez" {
  key_name = "GGEZ"
}

# ============================================================
# Step 1: Latest PyTorch Neuron DLAMI (Ubuntu 24.04)
# ============================================================

data "aws_ami" "neuron_pytorch_dlami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning AMI Neuron PyTorch 2.9 (Ubuntu 24.04)*"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# ============================================================
# Step 2: Launch inf2.xlarge
# ============================================================

resource "aws_instance" "inf2_neuron" {
  ami                         = data.aws_ami.neuron_pytorch_dlami.id
  instance_type               = "inf2.xlarge"
  key_name                    = data.aws_key_pair.ggez.key_name
  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.neuron_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size           = 200
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = "inf2-neuron-pytorch-dlami"
  }
}

# ============================================================
# Outputs
# ============================================================

output "ami_id"       { value = data.aws_ami.neuron_pytorch_dlami.id }
output "instance_id"  { value = aws_instance.inf2_neuron.id }
output "public_ip"    { value = aws_instance.inf2_neuron.public_ip }
output "ssh_command"  { value = "ssh -i GGEZ.pem ubuntu@${aws_instance.inf2_neuron.public_ip}" }
