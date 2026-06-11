from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, time

from patrol.models import JadwalRonda


class JadwalRondaForm(forms.Form):
    JAM_MULAI_WAJIB   = time(21, 0)
    JAM_SELESAI_WAJIB = time(5, 0)
    MIN_PETUGAS = 5
    MAX_PETUGAS = 7

    petugas_ids = forms.CharField()
    tanggal     = forms.DateField(input_formats=['%Y-%m-%d'])
    jam_mulai   = forms.TimeField(input_formats=['%H:%M'])
    jam_selesai = forms.TimeField(input_formats=['%H:%M'])
    blok_area   = forms.CharField(max_length=100, required=False)
    catatan_rt  = forms.CharField(required=False)
    items       = forms.CharField(required=False)

    # Di-set dari view saat mode edit agar validasi tanggal skip jadwal sendiri
    edit_pk = None

    def clean_petugas_ids(self):
        raw = self.data.get('petugas_ids_list', [])
        if not isinstance(raw, list):
            raise forms.ValidationError('Format petugas tidak valid.')
        if len(raw) < self.MIN_PETUGAS:
            raise forms.ValidationError(f'Minimal {self.MIN_PETUGAS} petugas harus dipilih.')
        if len(raw) > self.MAX_PETUGAS:
            raise forms.ValidationError(f'Maksimal {self.MAX_PETUGAS} petugas per jadwal.')

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

        hari_ini    = timezone.localdate()
        batas_akhir = hari_ini + timedelta(days=6)

        # Mode buat: tanggal harus dalam range hari ini s/d +6
        # Mode edit: boleh tanggal lama, tapi tetap cek duplikat
        if self.edit_pk is None:
            if tanggal < hari_ini:
                raise forms.ValidationError('Tanggal tidak boleh sebelum hari ini.')
            if tanggal > batas_akhir:
                raise forms.ValidationError(
                    f'Tanggal maksimal {batas_akhir.strftime("%d/%m/%Y")} (7 hari dari sekarang).'
                )

        # Cek duplikat tanggal untuk RT yang sama
        dibuat_oleh = self.data.get('dibuat_oleh_user')
        if dibuat_oleh:
            qs = JadwalRonda.objects.filter(
                dibuat_oleh=dibuat_oleh,
                tanggal=tanggal,
            )
            # Mode edit: exclude tanggal+jam jadwal yang sedang diedit
            if self.edit_pk:
                jadwal_lama = JadwalRonda.objects.filter(pk=self.edit_pk).first()
                if jadwal_lama:
                    qs = qs.exclude(
                        tanggal=jadwal_lama.tanggal,
                        jam_mulai=jadwal_lama.jam_mulai,
                        jam_selesai=jadwal_lama.jam_selesai,
                    )
            if qs.exists():
                raise forms.ValidationError(
                    f'Tanggal {tanggal.strftime("%d/%m/%Y")} sudah ada jadwal ronda. Pilih tanggal lain.'
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

    def get_items(self):
        raw = self.data.get('items_list', [])
        if isinstance(raw, list):
            return [i.strip() for i in raw if isinstance(i, str) and i.strip()]
        return []