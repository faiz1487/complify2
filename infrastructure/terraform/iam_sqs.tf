data "aws_iam_policy_document" "ecs_task_sqs" {
  statement {
    sid    = "SQSProcessingAccess"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [
      aws_sqs_queue.processing.arn,
      aws_sqs_queue.processing_dlq.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecs_task_sqs" {
  name   = "${var.project_name}-ecs-task-sqs"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_sqs.json
}
