output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "alb_arn" {
  value = aws_lb.this.arn
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "alb_sg_security_group_id" {
  value = aws_security_group.alb.id
}

output "alb_http_listener_arn" {
  value = aws_lb_listener.http.arn
}

output "default_target_group_arn" {
  value = aws_lb_target_group.default.arn
}
