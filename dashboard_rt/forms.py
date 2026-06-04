from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, time


class JadwalRondaForm(forms.Form):
    """
    Form validasi untuk membuat / mengedit Jadwal Ronda.
    Dipakai di views.py (jadwal_buat & jadwal_edit) via JSON payload.

    Aturan bisnis:
    - petugas_ids : list of User PK, minimal 5 maksimal 7
    - tanggal     : hari ini s/d hari ini + 6 (total 7 hari)
    - jam_mulai   : harus 21:00
    - jam_selesai : harus 05:00
    """

    JAM_MULAI_WAJIB   = time(21, 0)
    JAM_SELESAI_WAJIB = time(5, 0)
    MIN_PETUGAS = 5
    MAX_PETUGAS = 7

    # ── Field-field form ─────────────────────────────────────────
    petugas_ids = forms.CharField()          # akan di-parse jadi list
    tanggal     = forms.DateField(input_formats=['%Y-%m-%d'])
    jam_mulai   = forms.TimeField(input_formats=['%H:%M'])
    jam_selesai = forms.TimeField(input_formats=['%H:%M'])
    blok_area   = forms.CharField(max_length=100, required=False)
    catatan_rt  = forms.CharField(required=False)
    items       = forms.CharField(required=False)   # JSON list string

    # ── Validasi per-field ───────────────────────────────────────

    def clean_petugas_ids(self):
        """
        Terima list of int (sudah di-parse dari JSON sebelum masuk form).
        Validasi: tipe, jumlah (5–7), dan semua user exist & terverifikasi.
        """
        raw = self.data.get('petugas_ids_list', [])   # di-set manual dari view
        if not isinstance(raw, list):
            raise forms.ValidationError('Format petugas tidak valid.')

        if len(raw) < self.MIN_PETUGAS:
            raise forms.ValidationError(
                f'Minimal {self.MIN_PETUGAS} petugas harus dipilih.'
            )
        if len(raw) > self.MAX_PETUGAS:
            raise forms.ValidationError(
                f'Maksimal {self.MAX_PETUGAS} petugas per jadwal.'
            )

        # Pastikan semua ID valid dan user terverifikasi
        petugas_qs = User.objects.filter(
            pk__in=raw,
            profile__is_verified=True,
        ).select_related('profile')

        if petugas_qs.count() != len(raw):
            raise forms.ValidationError(
                'Satu atau lebih petugas tidak ditemukan atau belum terverifikasi.'
            )

        return list(petugas_qs)

    def clean_tanggal(self):
        tanggal = self.cleaned_data.get('tanggal')
        if not tanggal:
            return tanggal

        hari_ini   = timezone.localdate()
        batas_akhir = hari_ini + timedelta(days=6)

        if tanggal < hari_ini:
            raise forms.ValidationError('Tanggal tidak boleh sebelum hari ini.')
        if tanggal > batas_akhir:
            raise forms.ValidationError(
                f'Tanggal maksimal {batas_akhir.strftime("%d/%m/%Y")} '
                f'(7 hari dari sekarang).'
            )
        return tanggal

    def clean_jam_mulai(self):
        jam = self.cleaned_data.get('jam_mulai')
        if jam and jam != self.JAM_MULAI_WAJIB:
            raise forms.ValidationError(
                f'Jam mulai ronda harus {self.JAM_MULAI_WAJIB.strftime("%H:%M")}.'
            )
        return jam

    def clean_jam_selesai(self):
        jam = self.cleaned_data.get('jam_selesai')
        if jam and jam != self.JAM_SELESAI_WAJIB:
            raise forms.ValidationError(
                f'Jam selesai ronda harus {self.JAM_SELESAI_WAJIB.strftime("%H:%M")}.'
            )
        return jam

    # ── Helper: ambil items sebagai list ────────────────────────

    def get_items(self):
        """Return list of item deskripsi (string) yang tidak kosong."""
        raw = self.data.get('items_list', [])
        if isinstance(raw, list):
            return [i.strip() for i in raw if isinstance(i, str) and i.strip()]
        return []