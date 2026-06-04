from django.db import models
from patrol.models import JadwalRonda

class ItemPatroli(models.Model):
    """
    Catatan item patroli yang dibuat oleh Ketua RT per jadwal ronda.
    Nantinya tampil di dashboard petugas sebagai checklist tugas patroli.
    """
    jadwal      = models.ForeignKey(
        JadwalRonda,
        on_delete=models.CASCADE,
        related_name='item_patroli'
    )
    urutan      = models.PositiveSmallIntegerField(default=0)
    deskripsi   = models.CharField(max_length=200)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Item Patroli'
        verbose_name_plural = 'Item Patroli'
        ordering            = ['urutan', 'created_at']

    def __str__(self):
        return f"[{self.jadwal}] {self.deskripsi}"