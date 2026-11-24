# Aurora Serverless v2 PostgreSQL that scales to zero. After
# db_seconds_until_auto_pause without a connection it pauses and bills only
# storage; the next connection wakes it in about 15 seconds (30 or more after
# a day asleep). The app waits for that instead of failing, see
# DB_CONNECT_RETRY_SECONDS in lambda.tf.

resource "random_password" "db" {
  length = 32
  # The password travels inside DATABASE_URL; letters and digits need no escaping.
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_rds_cluster" "this" {
  cluster_identifier = local.name
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  # Same major version as the postgres:16 image used in development.
  engine_version = "16.15"

  database_name   = "trincheiras"
  master_username = "trincheiras"
  master_password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]

  storage_encrypted         = true
  backup_retention_period   = 7
  copy_tags_to_snapshot     = true
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final"

  serverlessv2_scaling_configuration {
    min_capacity             = 0
    max_capacity             = var.db_max_capacity
    seconds_until_auto_pause = var.db_seconds_until_auto_pause
  }

  lifecycle {
    # AWS applies minor upgrades in the maintenance window.
    ignore_changes = [engine_version]
  }
}

resource "aws_rds_cluster_instance" "this" {
  identifier         = "${local.name}-1"
  cluster_identifier = aws_rds_cluster.this.id
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version
  instance_class     = "db.serverless"

  lifecycle {
    ignore_changes = [engine_version]
  }
}

locals {
  database_url = format(
    "postgresql+psycopg://%s:%s@%s:%d/%s?sslmode=require",
    aws_rds_cluster.this.master_username,
    random_password.db.result,
    aws_rds_cluster.this.endpoint,
    aws_rds_cluster.this.port,
    aws_rds_cluster.this.database_name,
  )
}
