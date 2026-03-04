from django.db import models


class TokenScore(models.Model):
    token = models.OneToOneField("scanner.Token", on_delete=models.CASCADE, related_name="score")
    score = models.IntegerField(default=0)
    breakdown = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.token} → {self.score}/14"
