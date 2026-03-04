from django.db import models


class TradeEvent(models.Model):
    SIDE_CHOICES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]

    token = models.ForeignKey("scanner.Token", on_delete=models.CASCADE, related_name="trade_events")
    wallet = models.CharField(max_length=64)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    amount = models.FloatField(default=0)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.side} {self.token} by {self.wallet[:8]}..."
