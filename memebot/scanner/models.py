# scanner/models.py

from django.db import models

class Token(models.Model):
    mint = models.CharField(max_length=64, unique=True)
    symbol = models.CharField(max_length=32, null=True, blank=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()
    source = models.CharField(max_length=32)

    is_rejected = models.BooleanField(default=False)
    alert_sent = models.BooleanField(default=False)
    safety_flags = models.JSONField(null=True, blank=True, help_text="Cached Solsniffer response")
    last_scored_snapshot = models.ForeignKey(
        'PairSnapshot', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='scored_tokens',
    )

    def __str__(self):
        return self.symbol or self.mint


class PairSnapshot(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    pair_address = models.CharField(max_length=128)
    dex_id = models.CharField(max_length=64)
    liquidity_usd = models.FloatField(null=True)
    volume_24h = models.FloatField(null=True)
    buys_1h = models.IntegerField(default=0)
    sells_1h = models.IntegerField(default=0)
    price_change_5m = models.FloatField(null=True)
    traders_1h = models.IntegerField(default=0)
    captured_at = models.DateTimeField(auto_now_add=True)